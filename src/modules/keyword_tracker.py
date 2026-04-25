import time
import sys
import argparse
import threading

try:
    import speech_recognition as sr
except ImportError:
    print("Error: The 'SpeechRecognition' and 'PyAudio' libraries are required.")
    print("Please install them by running: pip install SpeechRecognition PyAudio")
    sys.exit(1)

try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    print("Error: Could not import GameInputHandler.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Keyword Tracking Accessibility Module')
    parser.add_argument('--player', type=str, default='1', help='Player number to control (1 or 2)')
    args = parser.parse_args()
    
    player_prefix = f"P{args.player}"
    
    # Needs to be a UDP client hooking natively into PyGame Host
    handler = GameInputHandler(is_server=False)
    
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    
    print(f"Starting Voice Keyword Tracker for {player_prefix}...")
    print("Calibrating to ambient noise. Please stay quiet for 2 seconds...")
    
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=2.0)
    except OSError:
        print("Microphone not found or inaccessible. Exiting.")
        sys.exit(1)
        
    print("Calibration complete. Speak keywords: 'UP', 'DOWN', 'LEFT', 'RIGHT', 'ACTION'")
    print("Press Ctrl+C to quit.")

    # We will track active durations to auto-release the keys since voice is discrete, 
    # but the PyGame expects continuous boolean frames while moving.
    # We'll set the key True for a defined burst duration upon hearing the keyword.
    BURST_DURATION = 0.7  # Seconds the impulse holds True after recognizing speech
    active_keys = {}
    
    def background_callback(recognizer, audio):
        try:
            # We use Google's free recognizer backend natively for prototyping
            text = recognizer.recognize_google(audio).lower()
            print(f">Voice Detected: '{text}'")
            
            if "up" in text:
                trigger_key("UP")
            if "down" in text:
                trigger_key("DOWN")
            if "left" in text:
                trigger_key("LEFT")
            if "right" in text:
                trigger_key("RIGHT")
            if "action" in text or "shoot" in text or "jump" in text or "space" in text:
                trigger_key("ACTION")
                
        except sr.UnknownValueError:
            pass # Did not understand audio / background noise
        except sr.RequestError as e:
            print(f"! Speech service unreachable: {e}")

    def trigger_key(direction):
        print(f"--> Transmitting: {player_prefix}_{direction}")
        handler.inject_input(player_prefix, direction, True)
        active_keys[direction] = time.time()

    # Start listening silently traversing isolated parallel thread
    # phrase_time_limit ensures we chop sentences quickly into 1-second chunks for lower latency parsing
    stop_listening = recognizer.listen_in_background(mic, background_callback, phrase_time_limit=1.5)

    try:
        while True:
            current_time = time.time()
            keys_to_clear = []
            
            for k, timestamp in active_keys.items():
                if current_time - timestamp > BURST_DURATION:
                    # Drop the active hook naturally after impulse decays
                    handler.inject_input(player_prefix, k, False)
                    keys_to_clear.append(k)
                    
            for k in keys_to_clear:
                del active_keys[k]
                
            time.sleep(0.05) # Yield CPU Thread
            
    except KeyboardInterrupt:
        print("\nExiting Voice Keyword Tracker...")
    finally:
        stop_listening(wait_for_stop=False)
        handler.stop()

if __name__ == "__main__":
    main()
