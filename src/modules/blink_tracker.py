import cv2
import time
import sys
import os
import urllib.request
import mediapipe as mp
import argparse
from scipy.spatial import distance as dist
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    import sys
    print("Error: Could not import GameInputHandler.")
    sys.exit(1)

def download_model():
    """Ensures the face landmarker module is downloaded for MediaPipe Tasks."""
    model_path = os.path.join('src', 'assets', 'face_landmarker.task')
    # Ensure directory exists
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    if not os.path.exists(model_path):
        print("Downloading face_landmarker model... Please wait.")
        url = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task'
        urllib.request.urlretrieve(url, model_path)
    return model_path

def eye_aspect_ratio(eye_landmarks):
    """
    Computes the Eye Aspect Ratio (EAR) given 6 specific eye landmarks.
    Indices: 0 (p1/inner), 1 (p2/top), 2 (p3/top), 3 (p4/outer), 4 (p5/bottom), 5 (p6/bottom)
    EAR = ( |p2-p6| + |p3-p5| ) / ( 2 * |p1-p4| )
    """
    # Vertical distances across the eyelid
    A = dist.euclidean((eye_landmarks[1].x, eye_landmarks[1].y), 
                       (eye_landmarks[5].x, eye_landmarks[5].y))
    B = dist.euclidean((eye_landmarks[2].x, eye_landmarks[2].y), 
                       (eye_landmarks[4].x, eye_landmarks[4].y))
    
    # Horizontal distance across the corners of the eye
    C = dist.euclidean((eye_landmarks[0].x, eye_landmarks[0].y), 
                       (eye_landmarks[3].x, eye_landmarks[3].y))
    
    if C == 0:
        return 0.0
    
    ear = (A + B) / (2.0 * C)
    return ear

def main():
    parser = argparse.ArgumentParser(description='Blink Tracking Accessibility Module')
    parser.add_argument('--player', type=str, default='1', help='Player number to control (1 or 2)')
    args = parser.parse_args()
    
    player_prefix = f"P{args.player}"
    
    # Instantiate the Handler completely seamlessly as an isolated client tracking module
    handler = GameInputHandler(is_server=False)

    # Attempt to load or download model
    model_path = download_model()
    
    # Configure MediaPipe Tasks Vision API
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1)
        
    landmarker = vision.FaceLandmarker.create_from_options(options)
    
    # Initialize Camera
    cap = cv2.VideoCapture(0)
    # Use extremely low resolution for speed since we only need basic landmarks
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        sys.exit(1)
        
    print(f"Starting Headless Blink Tracker for {player_prefix}...")
    print("Squeeze/close your eyes intentionally for ~0.5 seconds to trigger action.")
    print("Press Ctrl+C to quit.")
    
    # Standard 6-point eye landmark indices for MediaPipe
    LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
    
    # Tuning variables
    EAR_THRESHOLD = 0.20        # Adjust slightly if it's too sensitive or not sensitive enough
    BLINK_DURATION_REQ = 0.5    # How many seconds an eye closure must be held
    
    blink_start_time = None
    action_triggered = False
    
    try:
        while True:
            success, frame = cap.read()
            if not success:
                time.sleep(0.1)
                continue
                
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            
            # Detect face
            timestamp_ms = int(time.time() * 1000)
            results = landmarker.detect_for_video(mp_image, timestamp_ms)
            
            if results.face_landmarks:
                landmarks = results.face_landmarks[0]
                
                # Fetch spatial coordinates for computation
                left_eye_points = [landmarks[i] for i in LEFT_EYE_IDX]
                right_eye_points = [landmarks[i] for i in RIGHT_EYE_IDX]
                
                # Calculate independent EARs
                left_ear = eye_aspect_ratio(left_eye_points)
                right_ear = eye_aspect_ratio(right_eye_points)
                
                # Average both eyes
                avg_ear = (left_ear + right_ear) / 2.0
                
                # Check condition
                if avg_ear < EAR_THRESHOLD:
                    if blink_start_time is None:
                        # Start measuring blink duration
                        blink_start_time = time.time()
                    else:
                        elapsed = time.time() - blink_start_time
                        if elapsed >= BLINK_DURATION_REQ and not action_triggered:
                            print(f"{player_prefix}_ACTION")
                            
                            # Fire impulse properly isolating the prefix formatting seamlessly to queue
                            handler.inject_input(player_prefix, "ACTION", True)
                            
                            action_triggered = True  
                else:
                    # Target's eyes are open; reset state cleanly
                    if action_triggered:
                        handler.inject_input(player_prefix, "ACTION", False)
                        
                    blink_start_time = None
                    action_triggered = False
                    
            # Small sleep to conserve CPU in headless mode
            time.sleep(0.02)
            
    except KeyboardInterrupt:
        print("\nExiting Blink Tracker...")
    finally:
        handler.stop()
        cap.release()
        landmarker.close()

if __name__ == "__main__":
    main()
