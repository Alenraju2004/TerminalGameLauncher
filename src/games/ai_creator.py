import os
import sys
import subprocess
import random
from google import genai

def generate_terminal_game(p1_control_limitations, p2_control_limitations, game_theme):
    """
    Legacy wrapper signature. Repurposed to prompt the Gemini LLM for a custom, 
    standalone 2-player Pygame application based on a strictly defined set of rules.
    """
    
    # Initialize API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        api_key_path = os.path.join("data", "api_key")
        if os.path.exists(api_key_path):
            with open(api_key_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("AIza"):
                        api_key = line
                        break

    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment or 'api_key' file.")
        return None
    
    client = genai.Client(api_key=api_key)
    
    if game_theme and game_theme.strip():
        selected_theme = game_theme.strip()
    else:
        themes = [
            "Sumo", "Tag", "Racing", "Territory Capture",
            "Tron-Style Lightcycles", "Dodgeball / Artillery",
            "Asteroids-Style Space Duel", "Keep Away / Juggernaut"
        ]
        selected_theme = random.choice(themes)
    
    prompt = f"""
You are an expert Python developer.
Generate a complete, standalone 2-player local competitive game using the pygame library.

Game Concept: Randomly selected theme is {selected_theme}. The game must be a "Single Screen" experience with a clear win condition.

CRITICAL FEATURE: The Start/Rules Screen
- Initial State: The game must NOT start immediately. It must begin on a "Rules & Controls" screen.
- Content of Rules Page: 
  * Title: A large, bold title for the {selected_theme} game.
  * Controls: Clearly display "Player 1 Controls: D-Pad Only" and "Player 2 Controls: D-Pad Only".
  * Objective: A short sentence explaining the winning condition.
  * Interaction: Display "Press UP to Start" to enter the game safely. 
- Game Transition: Once the game is over, it should transition to a "Game Over" screen that displays the winner and a "Press UP to Restart" option to loop back.

Technical Constraints (To prevent errors):
- CRITICAL: Do NOT use pygame.key.get_pressed() or standard event queues for player movement. You MUST read inputs from a dictionary returned by GameInputHandler.get_state(). Player 1 exclusively uses the boolean keys "P1_UP", "P1_DOWN", "P1_LEFT", and "P1_RIGHT". Player 2 uses "P2_UP", etc. ACTION buttons are STRICTLY FORBIDDEN. Do not reference "P1_ACTION" or "P2_ACTION".
- State Machine: Use a simple variable (e.g., game_state = "START", "PLAY", "GAMEOVER") to toggle between the screens.
- Zero External Dependencies: Do NOT load images (.png, .jpg) or sounds. All text must be rendered using pygame.font.SysFont. All visuals must be pygame.draw shapes (rect, circle, line).
- Object-Oriented Design: Use a Player class to handle movement and a Game class to manage the state and state machine.
- Stable Timing: Implement pygame.time.Clock() and cap the frame rate at 60 FPS.
- Safe UI: Use pygame.font.SysFont for all rendering. Make sure to flip/update the display for every state to prevent flickering.
- Flexible Resolution Setup: Do not artificially restrict the resolution to 800x600. If the game demands a larger arena, define larger coordinate spaces like 1024x768 or 1280x720 automatically. Ensure players spawn gracefully within boundaries.
- Clean Exit: Include a standard event loop that handles pygame.QUIT to prevent the window from hanging on close.

VISUAL POLISH & AESTHETICS (CRITICAL):
- Palette: Do not use basic, boring colors. You must implement a "Neon/Cyberpunk" or "High-Contrast Arcade" color palette.
- Particle Effects: When players collide, score, or dash, generate an array of tiny expanding and fading shapes using pygame.Surface with SRCALPHA for transparency.
- Screen Shake: On major impacts or round ends, add a temporary random offset (e.g., +/- 5 pixels) to all drawing coordinates for 10-20 frames to simulate impact.
- Smooth Motion: Ensure players move using floating-point coordinates for physics, only casting to integers exclusively when calling pygame.draw functions.
- Typography: Draw drop-shadows behind all text on the UI screens by rendering the font twice (once in dark gray slightly offset, once in the primary color on top).

Code Structure:
1. Imports (pygame, sys, random). You MUST also unconditionally import GameInputHandler via try/except:
```python
try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    print("Error: Could not import GameInputHandler")
    sys.exit(1)
```
2. Constants (Colors, Screen Dim, FPS).
3. Player Class (Handles __init__, move, and draw updating via state dictionaries natively passed down).
4. Main Function:
   - Initialize Pygame.
   - Create a local `input_handler = GameInputHandler()`.
   - CRITICAL: GameInputHandler processes keyboard and tracker injections asynchronously in the background. Do NOT attempt to pass pygame events to it (e.g., do NOT write `input_handler.update(events)` or similar). 
   - Inside the `while True` loop, handle `pygame.QUIT`, then simply hook `state = input_handler.get_state()` and pass that mapping natively to your actors.
   - CRITICAL: The state dictionary ONLY contains exact booleans like "P1_UP" or "P2_LEFT". There are NO ACTION controls. To start or restart the game, simply check `if state.get("P1_UP") or state.get("P2_UP"):`.

Output: Provide ONLY the full, single-file runnable Python code. Ensure the logic for switching between the Rules Screen and the Game is robust and easy to read. Do not output markdown backticks (```python) or extraneous text.
"""

    print("--- Requesting Custom Pygame from AI ---")
    print(f"Selected Theme: {selected_theme}")
    print("Enforcing Hardware Accessibility Engine Requirements...")
    
    # Setup chat session for automated self-correction
    chat = client.chats.create(model='gemini-2.5-flash')
    
    max_retries = 3
    attempts = 0
    success = False
    output_filename = os.path.join("src", "games", "temp_game.py")
    current_prompt = prompt

    while attempts < max_retries:
        attempts += 1
        print(f"\nWaiting for generation... (Attempt {attempts}/{max_retries})")
        
        import time
        try:
            response = chat.send_message(current_prompt)
            code = response.text
        except Exception as e:
            err_msg = str(e).replace('\n', ' ')
            print(f"API Error Caught: {err_msg[:60]}... Retrying in 5s")
            time.sleep(5)
            continue
        
        # 1. Output Cleaning: Strip any markdown code formatting
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()
        
        # Save output candidate
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(code)
            
        print("Validating generated Python syntax...")
        # 3. Syntax Checking using py_compile
        result = subprocess.run([sys.executable, '-m', 'py_compile', output_filename], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\nGame successfully generated, validated, and saved to {output_filename}!")
            success = True
            break
        else:
            stderr_output = result.stderr.strip()
            print(f"Syntax Error Detected in AI Output:\n{stderr_output}")
            
            # 4. The Self-Correction Prompt
            if attempts < max_retries:
                print("Requesting AI to self-correct...")
                current_prompt = f"The Python code you generated had the following syntax/indentation error:\n{stderr_output}\nPlease rewrite the entire script to fix this error. Output ONLY the raw, corrected Python code."
            
    # 5. Fallback
    if not success:
        print("\nFailed to generate a stable game after 3 attempts.")
        if os.path.exists(output_filename):
            os.remove(output_filename) # Prevent launcher from executing broken file
        return None
        
    return output_filename

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--theme', type=str, default="", help="Custom theme prompt for the AI generator")
    args = parser.parse_args()
    
    generate_terminal_game("", "", args.theme)
