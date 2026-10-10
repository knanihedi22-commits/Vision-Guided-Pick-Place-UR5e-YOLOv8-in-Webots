from controller import Supervisor
import socket
import struct
import time

# -----------------------
# Webots initialization
# -----------------------
robot = Supervisor()
timestep = int(robot.getBasicTimeStep())

# Get camera (on UR5e)
camera = robot.getDevice("camera")
camera.enable(timestep)

# Get FIRST distance sensor (for object detection on conveyor)
distance_sensor = robot.getDevice("distance sensor")
distance_sensor.enable(timestep)

print("✅ UR5e devices initialized")

# -----------------------
# Get conveyor belt from scene
# -----------------------
conveyor = robot.getFromDef("CONVEYOR")
if conveyor is None:
    print("❌ Could not find conveyor with DEF name 'CONVEYOR'")
    exit(1)

print("✓ Found conveyor belt")
print(f"   Current speed: {conveyor.getField('speed').getSFFloat()}")

# -----------------------
# Socket to YOLO detector
# -----------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 8888))
sock.settimeout(5.0)
print("🔌 Connected to YOLO detector")

# -----------------------
# GRIP PARAMETERS - PERFECT SETTINGS
# -----------------------
APPLE_GRIP = {
    "finger_1_joint_1": 0.8,
    "finger_1_joint_2": 0.6,
    "finger_1_joint_3": 0.3,
    "finger_2_joint_1": 0.8,
    "finger_2_joint_2": 0.6,
    "finger_2_joint_3": 0.3,
    "finger_middle_joint_1": 0.8,
    "finger_middle_joint_2": 0.6,
    "finger_middle_joint_3": 0.3,
    "palm_finger_1_joint": 0.4,
    "palm_finger_2_joint": 0.4
}

CAN_BEER_GRIP = {
    "finger_1_joint_1": 0.85,
    "finger_1_joint_2": 0.65,
    "finger_1_joint_3": -0.35,
    "finger_2_joint_1": 0.75,
    "finger_2_joint_2": 0.55,
    "finger_2_joint_3": -0.25,
    "finger_middle_joint_1": 0.75,
    "finger_middle_joint_2": 0.55,
    "finger_middle_joint_3": -0.25,
    "palm_finger_1_joint": 0.45,
    "palm_finger_2_joint": 0.35
}

# -----------------------
# UR5e ARM JOINT NAMES
# -----------------------
UR5E_JOINTS = [
    "shoulder_pan_joint",
    "shoulder_lift_joint", 
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint"
]

# ZERO position for resetting arm
ZERO_POSITION = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # All joints at zero

# -----------------------
# GRIPPER CONTROL FUNCTIONS
# -----------------------
def open_gripper():
    """Open gripper fully"""
    print("🤖 Opening gripper...")
    
    open_positions = {
        "finger_1_joint_1": 0.05,
        "finger_1_joint_2": 0.0,
        "finger_1_joint_3": -0.05,
        "finger_2_joint_1": 0.05,
        "finger_2_joint_2": 0.0,
        "finger_2_joint_3": -0.05,
        "finger_middle_joint_1": 0.05,
        "finger_middle_joint_2": 0.0,
        "finger_middle_joint_3": -0.05,
        "palm_finger_1_joint": 0.0,
        "palm_finger_2_joint": 0.0
    }
    
    for joint_name, position in open_positions.items():
        try:
            joint = robot.getDevice(joint_name)
            joint.setPosition(position)
        except:
            pass
    
    for _ in range(100):
        robot.step(timestep)

def apply_grip(grip_params, object_name):
    """Apply specific grip parameters"""
    print(f"🎯 Applying {object_name} grip...")
    
    for joint_name, position in grip_params.items():
        try:
            joint = robot.getDevice(joint_name)
            joint.setPosition(position)
        except:
            pass
    
    # Wait for gripper to close (longer for cans/beer bottles)
    if "can" in object_name.lower() or "beer" in object_name.lower() or "bottle" in object_name.lower():
        wait_time = 200
    else:
        wait_time = 150
        
    for _ in range(wait_time):
        robot.step(timestep)

def grab_object(object_type):
    """Grab object based on its type"""
    print(f"\n🤖 GRABBING {object_type.upper()}")
    print("="*40)
    
    if "apple" in object_type.lower():
        apply_grip(APPLE_GRIP, "apple")
    elif "can" in object_type.lower() or "beer" in object_type.lower() or "bottle" in object_type.lower():
        apply_grip(CAN_BEER_GRIP, "can/beer bottle")
    else:
        print(f"⚠️ Unknown object type: {object_type}, using default grip")
        apply_grip(CAN_BEER_GRIP, "default")
    
    print("✅ Grab complete!")
    print("="*40)

# -----------------------
# UR5e ARM CONTROL FUNCTIONS
# -----------------------
def get_ur5e_joints():
    """Get UR5e arm joints"""
    joints = []
    for name in UR5E_JOINTS:
        try:
            joint = robot.getDevice(name)
            joint.setVelocity(0.3)  # Slower for stability
            joints.append(joint)
        except:
            print(f"⚠️ {name} not found")
            joints.append(None)
    
    return joints

def move_arm_to_position(target_positions, description="", steps=150):
    """Move arm to target joint positions smoothly"""
    if description:
        print(f"🦾 {description}")
    
    arm_joints = get_ur5e_joints()
    
    # Get current positions
    current_positions = []
    for joint in arm_joints:
        if joint:
            current_positions.append(joint.getTargetPosition())
        else:
            current_positions.append(0.0)
    
    # Smooth interpolation
    for step in range(steps):
        ratio = step / steps
        intermediate = []
        for i in range(6):
            if i < len(current_positions) and i < len(target_positions):
                interp = current_positions[i] + (target_positions[i] - current_positions[i]) * ratio
                intermediate.append(interp)
            else:
                intermediate.append(0.0)
        
        for i, joint in enumerate(arm_joints):
            if joint and i < len(intermediate):
                joint.setPosition(intermediate[i])
        
        robot.step(timestep)
        
        if step % 30 == 0:
            print(f"  Progress: {step/steps*100:.0f}%", end='\r')
    
    print("\n✅ Movement complete!")

def lift_arm_with_object():
    """Lift arm up while holding object"""
    print("\n🦾 LIFTING ARM WITH OBJECT")
    print("="*40)
    
    # Lift position
    LIFT_POSITION = [0, -3.14, 0, 0, 1, 0.0]
    
    # 1. Lift arm up
    move_arm_to_position(LIFT_POSITION, "Lifting arm up with object...", steps=2000)
    
    # 2. Hold for 2 seconds
    print("⏳ Holding object lifted (2 seconds)...")
    for i in range(2):
        for _ in range(100):
            robot.step(timestep)
        print(f"  {i+1}/2 seconds")
    
    print("✅ Lift complete!")
    print("="*40)

def reset_arm_to_zero():
    """Reset arm to zero position (all joints at 0)"""
    print("\n🔄 RESETTING ARM TO ZERO POSITION")
    
    # Move to zero position
    move_arm_to_position(ZERO_POSITION, "Moving to zero position...", steps=1600)
    
    print("✅ Arm is now in zero position, ready for next object!")

def execute_complete_cycle(object_type):
    """Execute complete cycle: grab, lift, release, reset to zero"""
    print(f"\n🚀 EXECUTING COMPLETE CYCLE FOR {object_type.upper()}")
    print("="*50)
    
    # 1. Grab the object
    grab_object(object_type)
    
    # 2. Lift the arm with the object
    lift_arm_with_object()
    
    # 3. Release the object
    print("🤖 Releasing object...")
    open_gripper()
    
    # 4. Hold position briefly after release
    print("⏳ Pausing after release...")
    for _ in range(50):
        robot.step(timestep)
    
    # 5. Reset arm to zero position
    reset_arm_to_zero()
    
    print("✅ Cycle complete! Ready for next object.")
    print("="*50)

# -----------------------
# Parameters
# -----------------------
DETECTION_THRESHOLD = 1
CONTACT_THRESHOLD = 21  # Threshold for gripper contact detection
DEBOUNCE_STEPS = 30
object_detected = False
contact_detected = False
debounce_counter = 0
detection_count = 0
current_object_type = None
gripper_monitoring_active = False

# Variable for the second distance sensor
distance_sensor2 = None

# Open gripper initially
print("\n🤖 Initializing system...")
open_gripper()

# Initialize arm joints (but don't move to zero position)
arm_joints = get_ur5e_joints()
if any(arm_joints):
    print("🦾 UR5e arm joints found")
    print("✅ System initialized! Arm stays in current position.")
    print("   Waiting for objects to arrive at the gripper...")
else:
    print("⚠️ No UR5e arm joints found, will continue without arm movement")

# Start conveyor
conveyor.getField("speed").setSFFloat(0.25)
print("▶ Conveyor started")

# -----------------------
# Main loop
# -----------------------
while robot.step(timestep) != -1:
    sensor_value = distance_sensor.getValue()
    
    # Update debounce counter
    if debounce_counter > 0:
        debounce_counter -= 1
    
    # Reset detection when object leaves conveyor sensor
    if sensor_value >= DETECTION_THRESHOLD:
        object_detected = False
    
    # ==============================================
    # OBJECT DETECTION ON CONVEYOR (First sensor)
    # ==============================================
    if sensor_value < DETECTION_THRESHOLD and not object_detected and debounce_counter == 0:
        print("🚨 Object detected under first sensor!")
        object_detected = True
        debounce_counter = DEBOUNCE_STEPS
        detection_count += 1
        
        print(f"\n{'='*50}")
        print(f"🚨 OBJECT DETECTED (#{detection_count})")
        print(f"   First sensor value: {sensor_value:.2f}")
        print(f"{'='*50}")

        # 1. STOP CONVEYOR
        print("⏹️ Stopping conveyor belt...")
        conveyor.getField("speed").setSFFloat(0.0)
        
        # Wait for conveyor to stop completely
        for i in range(10):
            robot.step(timestep)
            if i == 4:
                print("   Conveyor stopping...")

        # 2. CAPTURE IMAGE
        print("📸 Capturing image from camera...")
        image_data = camera.getImage()
        
        if not image_data:
            print("❌ Failed to capture image")
            # Restart conveyor and continue
            conveyor.getField("speed").setSFFloat(0.25)
            print("▶ Conveyor restarted")
            continue

        image_size = len(image_data)
        print(f"   Image captured: {image_size:,} bytes")

        # 3. SEND IMAGE TO YOLO
        print("📤 Sending image to YOLO detector...")
        try:
            # Send image size (4 bytes) then image data
            sock.send(struct.pack("!I", image_size))
            sock.sendall(image_data)
            print("   Image sent successfully")
            
            # 4. RECEIVE DETECTION RESULTS
            print("🔄 Waiting for detection results...")
            
            # Clear any old data in socket
            sock.settimeout(2.0)
            try:
                # Simple receive with timeout
                data = sock.recv(4096)
            except socket.timeout:
                data = b""
                print("⏱️  Timeout waiting for response")
            finally:
                sock.settimeout(5.0)
            
            # 5. PROCESS AND PRINT RESULTS
            print("\n📊 DETECTION RESULTS:")
            print("-" * 30)
            
            detected_type = None
            
            if data:
                try:
                    # Decode and split by lines
                    response = data.decode("utf-8").strip()
                    
                    if response:
                        # Split by newlines and remove empty strings
                        detected_objects = [obj.strip() for obj in response.split('\n') if obj.strip()]
                        
                        if detected_objects:
                            print(f"   Detected {len(detected_objects)} object(s):")
                            for i, obj in enumerate(detected_objects, 1):
                                print(f"   {i:2d}. {obj}")
                            
                            # Determine object type (prioritize first detection)
                            first_obj = detected_objects[0].lower()
                            
                            if "apple" in first_obj:
                                detected_type = "apple"
                            elif "can" in first_obj:
                                detected_type = "can"
                            elif "beer" in first_obj or "bottle" in first_obj:
                                detected_type = "beerbottle"
                            else:
                                # Try to infer from other keywords
                                if "bottle" in first_obj:
                                    detected_type = "beerbottle"
                                elif "drink" in first_obj or "soda" in first_obj:
                                    detected_type = "can"
                                else:
                                    detected_type = "unknown"  # default
                            
                            current_object_type = detected_type
                            print(f"🎯 Identified as: {detected_type}")
                            
                            # ==============================================
                            # ACTIVATE SECOND DISTANCE SENSOR (on gripper)
                            # ==============================================
                            print("\n🎯 Activating gripper contact sensor...")
                            try:
                                # Get the second distance sensor (on gripper)
                                distance_sensor2 = robot.getDevice("distance sensor(1)")
                                distance_sensor2.enable(timestep)
                                gripper_monitoring_active = True
                                print("✅ Gripper contact sensor activated")
                                print("   Waiting for object to reach gripper...")
                            except:
                                print("⚠️ Could not activate 'distance sensor(1)'")
                                print("   Make sure it exists on the gripper")
                                gripper_monitoring_active = False
                            
                        else:
                            print("   No objects detected")
                    else:
                        print("   Empty response")
                        
                except UnicodeDecodeError:
                    print(f"   Raw data received: {len(data)} bytes (could not decode)")
            else:
                print("   No response received")
                
            print("-" * 30)

        except socket.error as e:
            print(f"❌ Socket error: {e}")
            # Try to reconnect
            try:
                sock.close()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("localhost", 8888))
                sock.settimeout(5.0)
                print("🔌 Reconnected to YOLO detector")
            except:
                print("❌ Failed to reconnect")

        except Exception as e:
            print(f"❌ Unexpected error: {e}")

        # 6. RESTART CONVEYOR (object moves toward gripper)
        print("\n▶ Restarting conveyor belt...")
        conveyor.getField("speed").setSFFloat(0.25)
        print(f"   Conveyor speed set to: {conveyor.getField('speed').getSFFloat()}")
        
        print(f"{'='*50}\n")
    
    # ==============================================
    # MONITOR GRIPPER CONTACT SENSOR (Second sensor)
    # ==============================================
    if gripper_monitoring_active and distance_sensor2 and not contact_detected and current_object_type:
        try:
            # Read gripper contact sensor value
            contact_sensor_value = distance_sensor2.getValue()
            
            # Print the contact sensor value every few steps
            if robot.getTime() % 0.3 < 0.05:  # Print every ~0.3 seconds
                print(f"Gripper sensor: {contact_sensor_value:.3f}")
            
            # Check if object contacted the gripper
            if contact_sensor_value < CONTACT_THRESHOLD:
                print("\n" + "="*60)
                print(f"🤖 {current_object_type.upper()} REACHED GRIPPER!")
                print(f"   Gripper sensor value: {contact_sensor_value:.3f}")
                print(f"   Threshold: {CONTACT_THRESHOLD}")
                print("="*60)
                
                contact_detected = True
                
                # Stop conveyor since object reached gripper
                conveyor.getField("speed").setSFFloat(0.0)
                print("⏹️ Conveyor stopped - Object at gripper position")
                
                # Wait a moment for object to settle
                print("⏳ Waiting for object to settle...")
                for _ in range(30):
                    robot.step(timestep)
                
                # EXECUTE COMPLETE CYCLE
                if current_object_type != "unknown":
                    execute_complete_cycle(current_object_type)
                else:
                    print("⚠️ Unknown object type, skipping grab operation")
                
                # Wait before resetting
                for _ in range(50):
                    robot.step(timestep)
                
                # Reset for next object
                contact_detected = False
                gripper_monitoring_active = False
                object_detected = False
                current_object_type = None
                
                # Restart conveyor for next object
                conveyor.getField("speed").setSFFloat(0.25)
                print("\n▶ Conveyor restarted for next object")
                print("✅ Ready for next object!\n")
                
        except Exception as e:
            print(f"⚠️ Error reading gripper sensor: {e}")
            gripper_monitoring_active = False

# Cleanup
sock.close()
print("🔌 Socket connection closed")
print("👋 Program terminated")