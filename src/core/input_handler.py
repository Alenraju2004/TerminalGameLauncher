import time
import threading
import socket
import json
import sys

try:
    import keyboard
except ImportError:
    print("Error: The 'keyboard' library is required.")
    print("Please install it by running: pip install keyboard")
    sys.exit(1)

class GameInputHandler:
    def __init__(self, is_server=True):
        """
        is_server=True: Running inside the main Pygame instance. Hosts a UDP listener to receive tracker injections.
        is_server=False: Running inside an isolated tracker subprocess. Acts as a client projecting injections natively to the host UDP socket.
        """
        self.is_server = is_server
        self.port = 13013
        self.running = True
        
        # Comprehensive physical hardware lookup dictionary
        self._physical_state = {
            "P1_UP": False,    # W key
            "P1_DOWN": False,  # S key
            "P1_LEFT": False,  # A key
            "P1_RIGHT": False, # D key
            "P1_ACTION": False,# Spacebar
            
            "P2_UP": False,    # Up Arrow
            "P2_DOWN": False,  # Down Arrow
            "P2_LEFT": False,  # Left Arrow
            "P2_RIGHT": False, # Right Arrow
            "P2_ACTION": False,# Enter key
        }
        
        self._injected_state = {key: False for key in self._physical_state.keys()}
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        if self.is_server:
            # Bind to localhost to receive packets safely from isolated tracker modules
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('127.0.0.1', self.port))
            self.sock.setblocking(False)
            
            self.server_thread = threading.Thread(target=self._server_listener, daemon=True)
            self.server_thread.start()
            
            # The host physically continually polls native hardware Keyboards natively
            self.kb_thread = threading.Thread(target=self._keyboard_listener, daemon=True)
            self.kb_thread.start()

    def _server_listener(self):
        """Asynchronous UDP queue polling for OpenCV / Windows injection payloads."""
        while self.running:
            try:
                data, _ = self.sock.recvfrom(1024)
                if data:
                    msg = json.loads(data.decode('utf-8'))
                    key = msg.get("key")
                    val = msg.get("val")
                    if key is not None and val is not None:
                        self._injected_state[key] = val
            except BlockingIOError:
                time.sleep(0.005) # Maintain extreme 5ms latency 
            except Exception:
                time.sleep(0.01)

    def _keyboard_listener(self):
        """Polling mechanism parsing hard-coded OS keystrokes mapping."""
        while self.running:
            self._physical_state["P1_UP"] = keyboard.is_pressed('w')
            self._physical_state["P1_DOWN"] = keyboard.is_pressed('s')
            self._physical_state["P1_LEFT"] = keyboard.is_pressed('a')
            self._physical_state["P1_RIGHT"] = keyboard.is_pressed('d')
            self._physical_state["P1_ACTION"] = keyboard.is_pressed('space')
            
            self._physical_state["P2_UP"] = keyboard.is_pressed('up')
            self._physical_state["P2_DOWN"] = keyboard.is_pressed('down')
            self._physical_state["P2_LEFT"] = keyboard.is_pressed('left')
            self._physical_state["P2_RIGHT"] = keyboard.is_pressed('right')
            self._physical_state["P2_ACTION"] = keyboard.is_pressed('enter')
            
            time.sleep(0.01)

    def inject_input(self, player, action, is_active=True):
        """
        Allows external scripts to programmatically trigger an event.
        If this is a client (tracker subprocess), it transmits the state via UDP to the host game!
        """
        key = f"{player}_{action}"
        
        if not self.is_server:
            msg = json.dumps({"key": key, "val": is_active}).encode('utf-8')
            try:
                self.sock.sendto(msg, ('127.0.0.1', self.port))
            except Exception:
                pass
        else:
            self._injected_state[key] = is_active

    def get_state(self):
        """
        Returns the combined state of physical and injected inputs seamlessly across process boundaries.
        An action is active if EITHER the physical keyboard OR the tracker injection is active.
        """
        combined = {}
        for key in self._physical_state.keys():
            phys = self._physical_state.get(key, False)
            inj = self._injected_state.get(key, False)
            combined[key] = phys or inj
        return combined

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass

def main():
    print("Starting GameInputHandler local server...")
    print("Listening for UDP Payload Injections and standard Hardware Keyboard hooks natively...")
    print("Press 'q' to quit.\n")
    
    handler = GameInputHandler(is_server=True)
    
    try:
        # Simple Event Loop Debugger
        while True:
            if keyboard.is_pressed('q'):
                print("Quit requested.")
                break
                
            state = handler.get_state()
            
            active_inputs = [key for key, active in state.items() if active]
            if active_inputs:
                print(f"Active Hook: {', '.join(active_inputs)}")
                
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        pass
    finally:
        handler.stop()
        print("Event loop exited cleanly natively.")

if __name__ == "__main__":
    main()
