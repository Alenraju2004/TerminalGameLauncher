import cv2
import mediapipe as mp
import time
import sys
import os
import urllib.request
import argparse

try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    import sys
    print("Error: Could not import GameInputHandler.")
    sys.exit(1)

def download_model():
    model_path = os.path.join('src', 'assets', 'face_landmarker.task')
    # Ensure directory exists
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    if not os.path.exists(model_path):
        print("Downloading face_landmarker model... Please wait.")
        url = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task'
        urllib.request.urlretrieve(url, model_path)
        print("Download complete.")
    return model_path

def main():
    parser = argparse.ArgumentParser(description='Head Tracking Accessibility Module')
    parser.add_argument('--player', type=str, default='1', help='Player number to control (1 or 2)')
    args = parser.parse_args()
    
    player_prefix = f"P{args.player}"
    
    handler = GameInputHandler(is_server=False)

    # Attempt to download the required mediapipe model
    model_path = download_model()

    # Import the new Tasks API 
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    
    # Setup Face Landmarker Options
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1)
        
    landmarker = vision.FaceLandmarker.create_from_options(options)

    # Initialize Camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        sys.exit(1)
        
    NOSE_IDX = 1
    
    calibrated_x, calibrated_y = 0, 0
    calibration_frames = 20
    frame_count = 0
    
    THRESHOLD_X = 0.03
    THRESHOLD_Y = 0.04
    
    print(f"Starting Head Tracking for {player_prefix}... Please look straight at the camera to calibrate.")
    timestamp_ms = 0
    
    try:
        while True:
            success, image = cap.read()
            if not success:
                time.sleep(0.1)
                continue

            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
            
            timestamp_ms += int(1000 / 30) 
            results = landmarker.detect_for_video(mp_image, int(time.time() * 1000))

            # Reset state initially
            active_directions = {"UP": False, "DOWN": False, "LEFT": False, "RIGHT": False}

            if results.face_landmarks:
                nose = results.face_landmarks[0][NOSE_IDX]
                nx, ny = nose.x, nose.y
                
                if frame_count < calibration_frames:
                    calibrated_x += nx
                    calibrated_y += ny
                    frame_count += 1
                    if frame_count == calibration_frames:
                        calibrated_x /= calibration_frames
                        calibrated_y /= calibration_frames
                        print(f"{player_prefix} Calibrated! Tracking started. (Press Ctrl+C to stop)")
                else:
                    dx = nx - calibrated_x
                    dy = ny - calibrated_y
                    
                    if dy < -THRESHOLD_Y:
                        active_directions["UP"] = True
                    elif dy > THRESHOLD_Y:
                        active_directions["DOWN"] = True
                        
                    if dx < -THRESHOLD_X:
                        active_directions["RIGHT"] = True 
                    elif dx > THRESHOLD_X:
                        active_directions["LEFT"] = True
                        
            # Inject cleanly via the method requested
            for dir_name, is_active in active_directions.items():
                handler.inject_input(player_prefix, dir_name, is_active)
                if is_active:
                    print(f"{player_prefix}_{dir_name}")
                        
            time.sleep(0.01) 
            
    except KeyboardInterrupt:
        print("\nExiting Head Tracking...")
    finally:
        handler.stop()
        cap.release()
        landmarker.close()

if __name__ == "__main__":
    main()
