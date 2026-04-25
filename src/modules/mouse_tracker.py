import time
import sys
import threading
import argparse
from pynput import mouse, keyboard

try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    print("Error: Could not import GameInputHandler.")
    sys.exit(1)

ms_ctrl = mouse.Controller()

class MouseTrackingJoystick:
    def __init__(self, handler, player="P1"):
        self.handler = handler
        self.player = player
        
        # Grab initial physical center to trap the mouse
        self.center_x, self.center_y = ms_ctrl.position
        
        # Virtual cursor position (since physical cursor is trapped, this allows infinite drag)
        self.virtual_x = 0.0
        self.virtual_y = 0.0
        
        # The threshold the physical mouse must be dragged to trigger directional input
        self.deadzone = 50.0 
        
        self.running = True
        
        self.state = {
            "UP": False,
            "DOWN": False,
            "LEFT": False,
            "RIGHT": False,
            "ACTION_A": False,
            "ACTION_B": False
        }

    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.left:
            self.state["ACTION_A"] = pressed
            self.handler.inject_input(self.player, "ACTION_A", pressed)
            if pressed: 
                print(f"{self.player}: ACTION_A (Left Click)")
        elif button == mouse.Button.right:
            self.state["ACTION_B"] = pressed
            self.handler.inject_input(self.player, "ACTION_B", pressed)
            if pressed: 
                print(f"{self.player}: ACTION_B (Right Click)")
            
    def update_loop(self):
        print(f"Mouse Joystick Active for {self.player}. Mouse trapped inside Terminal at ({self.center_x}, {self.center_y}).")
        print("Move your physical mouse outside the deadzone to steer. Left/Right click for Actions.")
        print("PRESS 'ESC' ON YOUR KEYBOARD TO QUIT AND FREE THE MOUSE.")

        while self.running:
            # Calculate physical distance moved since the last frame
            curr_x, curr_y = ms_ctrl.position
            dx = curr_x - self.center_x
            dy = curr_y - self.center_y
            
            # Immediately snap the physical cursor back to center so it can never leave the terminal
            if dx != 0 or dy != 0:
                ms_ctrl.position = (self.center_x, self.center_y)
            
            # Apply continuous movement to the virtual joystick
            self.virtual_x += dx
            self.virtual_y += dy
            
            # Auto-centering spring (friction) so letting go of the mouse brings it back to neutral
            self.virtual_x *= 0.85
            self.virtual_y *= 0.85
            
            # Determine directions based on virtual joystick breaking the 'deadzone' bounds
            left_active = self.virtual_x < -self.deadzone
            right_active = self.virtual_x > self.deadzone
            up_active = self.virtual_y < -self.deadzone
            down_active = self.virtual_y > self.deadzone
            
            # Inject inputs to the Game Handler if they changed applying formatting bindings natively
            if left_active != self.state["LEFT"]:
                self.state["LEFT"] = left_active
                self.handler.inject_input(self.player, "LEFT", left_active)
                if left_active: print(f"{self.player}: LEFT")
                
            if right_active != self.state["RIGHT"]:
                self.state["RIGHT"] = right_active
                self.handler.inject_input(self.player, "RIGHT", right_active)
                if right_active: print(f"{self.player}: RIGHT")
                
            if up_active != self.state["UP"]:
                self.state["UP"] = up_active
                self.handler.inject_input(self.player, "UP", up_active)
                if up_active: print(f"{self.player}: UP")
                
            if down_active != self.state["DOWN"]:
                self.state["DOWN"] = down_active
                self.handler.inject_input(self.player, "DOWN", down_active)
                if down_active: print(f"{self.player}: DOWN")

            # 50Hz polling rate
            time.sleep(0.02) 
            
    def stop(self):
        self.running = False

def main():
    parser = argparse.ArgumentParser(description='Mouse Tracking Joystick')
    parser.add_argument('--player', type=str, default='1', help='Player number to control (1 or 2)')
    args = parser.parse_args()
    
    player_prefix = f"P{args.player}"
    
    handler = GameInputHandler(is_server=False)
    joystick = MouseTrackingJoystick(handler, player=player_prefix)
    
    # We do NOT use suppress=True globally because that breaks Windows cursor movement detection entirely.
    # By physically trapping the mouse in the `update_loop`, it can never reach other windows to click on them.
    
    # Furthermore, we use a global windows hook to strictly intercept and discard Mouse Button clicks natively
    # so even if the mouse was hovering over something, clicking doesn't interact with the OS while this script runs.
    def win32_event_filter(msg, data):
        # 0x0201 = WM_LBUTTONDOWN, 0x0202 = WM_LBUTTONUP
        # 0x0204 = WM_RBUTTONDOWN, 0x0205 = WM_RBUTTONUP
        if msg in (0x0201, 0x0202, 0x0204, 0x0205):
            mouse_listener.suppress_event()
            return False # Stop propagation
        return True
            
    if sys.platform == "win32":
        mouse_listener = mouse.Listener(
            on_click=joystick.on_click,
            win32_event_filter=win32_event_filter
        )
    else:
        mouse_listener = mouse.Listener(on_click=joystick.on_click)

    thread = threading.Thread(target=joystick.update_loop, daemon=True)
    thread.start()
    mouse_listener.start()

    # Hardware Keyboard Kill Switch (CRITICAL when messing with mouse captures)
    def on_press(key):
        if key == keyboard.Key.esc:
            return False

    with keyboard.Listener(on_press=on_press) as kbd_listener:
        kbd_listener.join()
        
    print("\nESC Pressed. Restoring Mouse Control...")
    joystick.stop()
    mouse_listener.stop()
    handler.stop()

if __name__ == "__main__":
    main()
