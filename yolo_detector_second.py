import socket
import struct
import numpy as np
import cv2
import os
from ultralytics import YOLO
from datetime import datetime

# Create folder for saving inference images
os.makedirs('connection_img/inference', exist_ok=True)

# Load your trained YOLO model
print("Loading trained YOLO model...")
model = YOLO('runs/train/object_detection/weights/best.pt')
print("✅ YOLO model loaded successfully!")

# Set up socket to receive images
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('localhost', 8888))
sock.listen(1)
print("🔌 Waiting for Webots connection on port 8888...")

conn, addr = sock.accept()
print(f"✅ Connected to Webots from {addr}")

# Webots camera resolution
width, height = 640, 640

# CONTINUOUS LOOP TO HANDLE MULTIPLE IMAGES
detection_count = 0
while True:
    print(f"\n🔄 Waiting for image #{detection_count + 1}...")
    
    # Receive image size
    size_data = conn.recv(4)
    if size_data:
        size = struct.unpack('!I', size_data)[0]
        print(f"📦 Receiving image of size: {size} bytes")
        
        # Receive image data
        image_data = b''
        while len(image_data) < size:
            chunk = conn.recv(size - len(image_data))
            if not chunk:
                break
            image_data += chunk
        
        if len(image_data) == size:
            print(f"✅ Image received successfully!")
            detection_count += 1
            
            # Reshape image (Webots sends BGRA format)
            image = np.frombuffer(image_data, np.uint8).reshape((height, width, 4))
            
            # Remove alpha channel, keep BGR (maintains correct colors)
            image_bgr = image[:, :, :3]
            
            # Run YOLO inference (YOLO accepts BGR format)
            print("🔍 Running YOLO inference...")
            results = model(image_bgr, conf=0.5)
            
            # Get the annotated image with bounding boxes
            annotated_image = results[0].plot()  # This returns BGR image with boxes
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            inference_filename = f"connection_img/inference/detection_{timestamp}.jpg"
            
            # Save the inference image
            cv2.imwrite(inference_filename, annotated_image)
            print(f"💾 Inference image saved: {inference_filename}")
            
            # Display detection results
            detected_objects = []
            for box in results[0].boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                detected_objects.append(f"{class_name}({confidence:.2f})")
            
            # Decide what object to send back - PICK HIGHEST CONFIDENCE ONLY
            if results[0].boxes and len(results[0].boxes) > 0:
                # Find the highest confidence detection
                highest_confidence = 0
                best_object = None
                
                for box in results[0].boxes:
                    class_id = int(box.cls[0])
                    class_name = model.names[class_id]
                    confidence = float(box.conf[0])
                    
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        best_object = class_name
                
                # Send only the highest confidence object
                message = best_object
                print(f"📤 Sending detected object: {best_object} (confidence: {highest_confidence:.2f})")
            else:
                message = "none"
                print("📤 No objects detected, sending 'none'")

            # Send result back to Webots
            conn.send(message.encode("utf-8"))
            
        else:
            print(f"❌ Image data incomplete: received {len(image_data)}/{size} bytes")

conn.close()
sock.close()
print("🔌 Connection closed")


#-----first version---
"""import socket
import struct
import numpy as np
import cv2
import os
from ultralytics import YOLO
from datetime import datetime

# Create folder for saving inference images
os.makedirs('connection_img/inference', exist_ok=True)

# Load your trained YOLO model
print("Loading trained YOLO model...")
model = YOLO('runs/train/object_detection/weights/best.pt')
print("✅ YOLO model loaded successfully!")

# Set up socket to receive images
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('localhost', 8888))
sock.listen(1)
print("🔌 Waiting for Webots connection on port 8888...")

conn, addr = sock.accept()
print(f"✅ Connected to Webots from {addr}")

# Webots camera resolution
width, height = 640, 640

# CONTINUOUS LOOP TO HANDLE MULTIPLE IMAGES
detection_count = 0
while True:
    print(f"\n🔄 Waiting for image #{detection_count + 1}...")
    
    # Receive image size
    size_data = conn.recv(4)
    if size_data:
        size = struct.unpack('!I', size_data)[0]
        print(f"📦 Receiving image of size: {size} bytes")
        
        # Receive image data
        image_data = b''
        while len(image_data) < size:
            chunk = conn.recv(size - len(image_data))
            if not chunk:
                break
            image_data += chunk
        
        if len(image_data) == size:
            print(f"✅ Image received successfully!")
            detection_count += 1
            
            # Reshape image (Webots sends BGRA format)
            image = np.frombuffer(image_data, np.uint8).reshape((height, width, 4))
            
            # Remove alpha channel, keep BGR (maintains correct colors)
            image_bgr = image[:, :, :3]
            
            # Run YOLO inference (YOLO accepts BGR format)
            print("🔍 Running YOLO inference...")
            results = model(image_bgr, conf=0.5)
            
            # Get the annotated image with bounding boxes
            annotated_image = results[0].plot()  # This returns BGR image with boxes
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            inference_filename = f"connection_img/inference/detection_{timestamp}.jpg"
            
            # Save the inference image
            cv2.imwrite(inference_filename, annotated_image)
            print(f"💾 Inference image saved: {inference_filename}")
            
            # Display detection results
            detected_objects = []
            for box in results[0].boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                detected_objects.append(f"{class_name}({confidence:.2f})")
            
            # Decide what object to send back
            if results[0].boxes and len(results[0].boxes) > 0:
                # Get ALL detected objects, not just the first one
                all_objects = []
                for box in results[0].boxes:
                    class_id = int(box.cls[0])
                    class_name = model.names[class_id]
                    confidence = float(box.conf[0])
                    all_objects.append(class_name)
                
                # Send all objects separated by newlines
                message = "\n".join(all_objects)
                print(f"📤 Sending {len(all_objects)} detected object(s): {', '.join(all_objects)}")
            else:
                message = "none"
                print("📤 Sending detected object: none")

            # Send result back to Webots
            conn.send(message.encode("utf-8"))
            
        else:
            print(f"❌ Image data incomplete: received {len(image_data)}/{size} bytes")

conn.close()
sock.close()
print("🔌 Connection closed")"""