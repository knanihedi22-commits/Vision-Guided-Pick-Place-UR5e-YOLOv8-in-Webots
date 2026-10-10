# Vision-Guided-Pick-Place-UR5e-YOLOv8-in-Webots
A robotic pick-and-place simulation in **Webots** where a **UR5e arm** with a **Robotiq 3F gripper** identifies objects on a conveyor belt using a custom-trained **YOLOv8** model, then picks each one with a grip profile tuned to its type.

The Webots controller (robot side) and the YOLO detector (AI side) run as two separate processes and communicate over a **TCP socket**. This keeps the heavy deep-learning stack (PyTorch / Ultralytics) outside the Webots Python environment.

---

## How it works

```
            ┌──────────────────────────── Webots ────────────────────────────┐
            │  Conveyor ──► Distance sensor #1 detects object                │
            │                   │                                            │
            │                   ▼                                            │
            │         Stop belt, capture 640×640 camera frame                │
            │                   │                                            │
            └───────────────────┼────────────────────────────────────────────┘
                                │  TCP (localhost:8888)
                                │  [4-byte size][BGRA image bytes]
                                ▼
                  ┌────────────────────────────┐
                  │  yolo_detector_second.py   │
                  │  YOLOv8 inference (conf≥0.5)│
                  │  saves annotated image     │
                  └─────────────┬──────────────┘
                                │  class name of highest-confidence detection
                                ▼
            ┌───────────────────────────── Webots ───────────────────────────┐
            │  Restart belt ──► Distance sensor #2 (on gripper) detects      │
            │  arrival ──► stop belt ──► grip ──► lift ──► release ──► reset │
            └────────────────────────────────────────────────────────────────┘
```

### Step by step

1. The conveyor runs at 0.25 m/s.
2. A distance sensor detects an object and the belt stops.
3. The arm-mounted camera captures a frame, which is sent to the detector.
4. YOLOv8 runs inference and replies with the label of the **most confident detection** (or `none`). An annotated image is saved to `connection_img/inference/`.
5. The controller maps the label to a type (`apple`, `can`, `beerbottle`, or `unknown`) and arms a second distance sensor on the gripper.
6. The belt restarts. When the object reaches the gripper, the belt stops and the full cycle runs: **grip → lift → release → return to zero pose**.
7. The belt restarts and the system waits for the next object.

---

## Repository contents

| File | Role |
|---|---|
| `train_yolo.py` | Fine-tunes YOLOv8n on a custom dataset, validates it (mAP50 / mAP50-95) and exports to ONNX |
| `yolo_detector_second.py` | Socket server that receives camera frames from Webots, runs YOLO, and returns the detected class. Includes the earlier "send all objects" version as a commented block |
| `merge_test.py` | Webots **supervisor controller** for the UR5e: conveyor control, sensor logic, socket client, gripper and arm motion |
| `nnnnn.wbt` | Webots world (R2025a): UR5e on a pedestal, Robotiq 3F gripper, camera, two distance sensors, conveyor belts, sorting ramp, crates, and test objects (apple, orange, beer bottle, cans) |

---

## Requirements

- [Webots R2025a](https://cyberbotics.com/)
- Python 3.9+
- Packages:

```bash
pip install ultralytics torch opencv-python numpy
```

The world file references `../protos/ConveyorBelt.proto` and `../protos/UR5e.proto`, which come from the Webots sample projects. Place the world inside the matching Webots project folder (for example the *Universal Robots* sample) so these relative paths resolve.

---

## Usage

### 1. Prepare the dataset and train

Edit the dataset path in `train_yolo.py` to point to your YOLO-format `data.yaml`:

```python
data_yaml = '/path/to/yolo_dataset/data.yaml'
```

Then train:

```bash
python train_yolo.py
```

Default settings: YOLOv8n, 100 epochs, image size 640, batch 16, early stopping patience 20. Weights are saved to `runs/train/object_detection/weights/best.pt`, and the model is also exported to ONNX.

### 2. Start the detector first

It acts as the server and waits for Webots to connect:

```bash
python yolo_detector_second.py
```

### 3. Run the simulation

Open `nnnnn.wbt` in Webots and press play. The `UR5e` node uses `merge_test` as its controller and runs as a supervisor (needed to control the conveyor speed).

---

## Grasp profiles

Each profile sets the joint targets of the Robotiq 3F fingers:

| Detected class | Profile | Notes |
|---|---|---|
| `apple` | `APPLE_GRIP` | Round, wide curl |
| `can`, `beer` / `bottle` | `CAN_BEER_GRIP` | Wrapped grip with longer settle time |
| anything else | `unknown` | Grasp is skipped |

---

## Communication protocol

| Direction | Payload |
|---|---|
| Webots → Detector | 4-byte big-endian unsigned int (image size) followed by raw **BGRA** pixels (640 × 640 × 4) |
| Detector → Webots | UTF-8 string with the class name of the highest-confidence detection, or `none` |

---

## Known limitations and ideas

- **Class names**: the controller matches on substrings (`apple`, `can`, `beer`, `bottle`). Your dataset's class names must contain these. The world also contains an `Orange`, which the controller currently treats as `unknown` (not grasped).
- **Open-loop motion**: arm poses are fixed joint targets, not computed with inverse kinematics, so grasping depends on objects stopping at a consistent position.
- **Hard-coded paths and ports**: the dataset path, model path, and port `8888` are fixed in the scripts.
- **Detector loop**: if Webots disconnects, the detector's `while True` loop does not exit cleanly. Handling an empty `recv()` would fix this.
- **Optimizer settings**: `lr0 = 0.01` is high for Adam; AdamW with `lr0 ≈ 0.001`, or the default SGD, is usually safer.
- **Ideas**: inverse kinematics for adaptive grasping, sorting objects into the crates by class, multi-object handling, and a confidence-based rejection step.
