import curses
import os
import sys
import subprocess
import glob
import threading
import queue

def draw_menu(stdscr, selected_row_idx, options, title):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    # Draw title
    title_x = max(0, w // 2 - len(title) // 2)
    title_y = max(0, h // 2 - len(options) // 2 - 2)
    stdscr.addstr(title_y, title_x, title)
    
    for idx, row in enumerate(options):
        x = max(0, w // 2 - len(row) // 2)
        y = max(0, h // 2 - len(options) // 2 + idx)
        
        if row.startswith("---") or row == "":
            stdscr.attron(curses.color_pair(2)) # Header formatting visually distinct
            stdscr.addstr(y, x, row)
            stdscr.attroff(curses.color_pair(2))
        elif idx == selected_row_idx:
            stdscr.attron(curses.color_pair(1)) # Highlighted selection
            stdscr.addstr(y, x, row)
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(y, x, row)
            
    stdscr.refresh()

def select_input_method(stdscr, player_name, exclude_option=None):
    options = ["Keyboard", "Head Tracking", "Voice Commands", "Blink Tracking (Eye Movement)", "One-Handed Mouse"]
    
    # Prevent assigning the same hardware tracker to both players simultaneously 
    if exclude_option and exclude_option != "Keyboard" and exclude_option in options:
        options.remove(exclude_option)
        
    options.append("< Go Back >")
    
    current_row = 0
    
    while True:
        draw_menu(stdscr, current_row, options, f"Select Input Method for {player_name}")
        key = stdscr.getch()
        
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(options) - 1:
            current_row += 1
        elif key in [10, 13]:  # Enter key
            return options[current_row]
        elif key == 27:        # ESC Key
            return "< Go Back >"

def prompt_text(stdscr, prompt_msg):
    """Prompts the user for a textual input."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    x = max(0, w // 2 - len(prompt_msg) // 2)
    y = h // 2 - 1
    stdscr.addstr(y, x, prompt_msg)
    stdscr.refresh()
    
    curses.echo()
    curses.curs_set(1)
    
    # Render input caret centered below
    input_str = stdscr.getstr(y + 2, w // 2 - 15, 30).decode('utf-8')
    
    curses.noecho()
    curses.curs_set(0)
    return input_str.strip()

def get_local_games():
    """Identifies python games in the src/games directory."""
    games_dir = os.path.join("src", "games")
    if not os.path.exists(games_dir):
        return []
    
    system_files = {
        "__init__.py",
        "ai_creator.py"
    }
    
    games = []
    # Search in src/games instead of current directory
    for file in os.listdir(games_dir):
        if file.endswith(".py") and file not in system_files:
            games.append(file)
            
    return sorted(games)

def launch_trackers(p1_ctrl, p2_ctrl):
    """
    Parses control schemes to spin up OpenCV/Pynput/Speech hardware modules as distinct 
    OS processes, avoiding GIL blockers and isolating camera/mic access.
    """
    processes = []
    
    def spawn_tracker(ctrl, player_num):
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() # Ensure src.core can be imported
        
        if ctrl == "Head Tracking":
            return subprocess.Popen([sys.executable, os.path.join("src", "modules", "head_tracker.py"), "--player", str(player_num)], env=env)
        elif ctrl in ["Blink Tracking (Eye Movement)", "Eye Tracking"]:
            return subprocess.Popen([sys.executable, os.path.join("src", "modules", "blink_tracker.py"), "--player", str(player_num)], env=env)
        elif ctrl == "One-Handed Mouse":
            return subprocess.Popen([sys.executable, os.path.join("src", "modules", "mouse_tracker.py"), "--player", str(player_num)], env=env)
        elif ctrl == "Voice Commands":
            return subprocess.Popen([sys.executable, os.path.join("src", "modules", "keyword_tracker.py"), "--player", str(player_num)], env=env)
        return None

    p1_proc = spawn_tracker(p1_ctrl, 1)
    if p1_proc: processes.append(p1_proc)
        
    p2_proc = spawn_tracker(p2_ctrl, 2)
    if p2_proc: processes.append(p2_proc)
        
    return processes

def main(stdscr):
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE) # Regular selection
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Header text
    
    while True:
        local_games = get_local_games()
        main_menu_options = []
        
        # Build categorical menu
        main_menu_options.append("--- LOCAL GAME LIBRARY ---")
        for game in local_games:
            main_menu_options.append(f"Play: {game}")
            
        main_menu_options.append("")
        main_menu_options.append("--- CREATOR TOOLS ---")
        main_menu_options.append("Generate AI Game")
        main_menu_options.append("Exit")
        
        # Start selector safely on the first actual game, bypassing headers
        current_row = 0
        while current_row < len(main_menu_options) and (main_menu_options[current_row].startswith("---") or main_menu_options[current_row] == ""):
            current_row += 1
            
        while True:
            draw_menu(stdscr, current_row, main_menu_options, "Terminal Game Launcher")
            key = stdscr.getch()
            
            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
                while current_row > 0 and (main_menu_options[current_row].startswith("---") or main_menu_options[current_row] == ""):
                    current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(main_menu_options) - 1:
                current_row += 1
                while current_row < len(main_menu_options) - 1 and (main_menu_options[current_row].startswith("---") or main_menu_options[current_row] == ""):
                    current_row += 1
            elif key in [10, 13]:
                if not (main_menu_options[current_row].startswith("---") or main_menu_options[current_row] == ""):
                    break
                
        selection = main_menu_options[current_row]
        if selection == "Exit":
            break
            
        if selection == "Generate AI Game":
            ai_options = ["Surprise Me (Random Theme)", "Enter Custom Theme", "< Go Back >"]
            ai_row = 0
            while True:
                draw_menu(stdscr, ai_row, ai_options, "AI Generator Module")
                key = stdscr.getch()
                if key == curses.KEY_UP and ai_row > 0: ai_row -= 1
                elif key == curses.KEY_DOWN and ai_row < len(ai_options)-1: ai_row += 1
                elif key in [10, 13]: break
                elif key == 27: ai_row = 2; break
                
            if ai_options[ai_row] == "< Go Back >":
                continue
                
            theme_arg = ""
            if ai_options[ai_row] == "Enter Custom Theme":
                theme_arg = prompt_text(stdscr, "Enter a short prompt (e.g., 'A stealth game with lasers'):")
                if not theme_arg.strip():
                    continue
                    
            p1_input = select_input_method(stdscr, "Player 1")
            if p1_input == "< Go Back >": continue
            
            p2_input = select_input_method(stdscr, "Player 2", exclude_option=p1_input)
            if p2_input == "< Go Back >": continue

            cmd = [sys.executable, os.path.join("src", "games", "ai_creator.py")]
            if theme_arg:
                cmd.extend(["--theme", theme_arg])
                
            # Execute Generative Script Asynchronously to stream telemetry 
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            # Subprocess STDOUT Reader Queue Thread
            q = queue.Queue()
            def reader_thread(pipe, out_q):
                for line in iter(pipe.readline, ''):
                    out_q.put(line.strip())
                pipe.close()
                
            t = threading.Thread(target=reader_thread, args=(proc.stdout, q))
            t.daemon = True
            t.start()
            
            import time
            start_time = time.time()
            expected_total_time = 15.0 # Average AI Synthesizer baseline duration
            
            log_lines = []
            h, w = stdscr.getmaxyx()
            stdscr.nodelay(True) # Ensure rendering loop does not block on keypresses
            
            while proc.poll() is None:
                while not q.empty():
                    log_lines.append(q.get())
                    # Cap array size cleanly showing only recent console outputs
                    if len(log_lines) > 8:
                        log_lines.pop(0)

                stdscr.clear()
                
                # Calculate synthetic deterministic progress visually
                elapsed = time.time() - start_time
                progress = min(elapsed / expected_total_time, 0.99) # Cap at 99% securely until subprocess naturally exits
                bar_width = min(50, w - 10)
                filled_len = int(bar_width * progress)
                bar = '█' * filled_len + '░' * (bar_width - filled_len)
                percentage = int(progress * 100)
                
                title = f"Synthesizing Game Arena... {percentage}%"
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(max(0, h//2 - 7), max(0, w//2 - len(title)//2), title)
                stdscr.attroff(curses.color_pair(2))
                
                # Render the visually pleasing progress bar
                bar_text = f"[{bar}]"
                stdscr.addstr(max(0, h//2 - 5), max(0, w//2 - len(bar_text)//2), bar_text)
                
                # Render Console Lines beautifully parsed inside the Native UI below the bar
                for i, line in enumerate(log_lines):
                    display_line = line[:w-2]
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(max(0, h//2 - 3 + i), max(0, w//2 - len(display_line)//2), display_line)
                    
                stdscr.refresh()
                curses.napms(100) # Throttle frame loop
                
            stdscr.nodelay(False)
            curses.endwin() # Handover terminal ownership to Pygame
            
            temp_game_path = os.path.join("src", "games", "temp_game.py")
            if os.path.exists(temp_game_path) and proc.returncode == 0:
                print("Loading Accessibility Hardware Drivers...")
                trackers = launch_trackers(p1_input, p2_input)
                
                print("Booting Synthesized Application...")
                env = os.environ.copy()
                env["PYTHONPATH"] = os.getcwd()
                try:
                    subprocess.run([sys.executable, temp_game_path, p1_input, p2_input], env=env)
                finally:
                    for proc_t in trackers:
                        proc_t.terminate()
                
                # Re-Initialize Curses gracefully returning from the external process
                stdscr = curses.initscr()
                curses.noecho()
                curses.cbreak()
                stdscr.keypad(True)
                curses.curs_set(0)
                curses.start_color()
                curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
                curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)

                h, w = stdscr.getmaxyx()
                save_msg = "Game Session Ended! Would you like to save this game to your local library? (Y/N)"
                
                while True:
                    stdscr.clear()
                    stdscr.addstr(h // 2, max(0, w // 2 - len(save_msg) // 2), save_msg)
                    stdscr.refresh()
                    
                    ans = stdscr.getch()
                    
                    if ans in [ord('y'), ord('Y'), 10, 13]:
                        name = prompt_text(stdscr, "Enter a short name (e.g., 'Tron', 'Air_Hockey'):")
                        if name:
                            clean_name = name.replace(" ", "_").strip()
                            if not clean_name.endswith(".py"):
                                clean_name += ".py"
                                
                            try:
                                os.rename(temp_game_path, os.path.join("src", "games", clean_name))
                                stdscr.clear()
                                succ_msg = f"Game saved securely as {clean_name}!"
                                stdscr.addstr(h // 2, max(0, w // 2 - len(succ_msg) // 2), succ_msg)
                                stdscr.refresh()
                                curses.napms(1500)
                            except OSError:
                                pass
                        break
                        
                    elif ans in [ord('n'), ord('N'), 27]:
                        try:
                            os.remove(temp_game_path)
                        except OSError:
                            pass
                        break
            else:
                stdscr = curses.initscr() 
                curses.noecho()
                curses.cbreak()
                stdscr.keypad(True)
                curses.curs_set(0)
                
                stdscr.clear()
                h, w = stdscr.getmaxyx()
                err_msg = "Error: Generator failed or was aborted. Press any key to return."
                stdscr.addstr(h // 2, max(0, w // 2 - len(err_msg) // 2), err_msg)
                stdscr.refresh()
                stdscr.getch()
                
        else:
            # Native Play Routine
            p1_input = select_input_method(stdscr, "Player 1")
            if p1_input == "< Go Back >":
                continue
                
            p2_input = select_input_method(stdscr, "Player 2", exclude_option=p1_input)
            if p2_input == "< Go Back >":
                continue
                
            if selection.startswith("Play: "):
                game_file = selection.replace("Play: ", "")
                curses.endwin()
                
                print(f"Loading Accessibility Drivers...")
                trackers = launch_trackers(p1_input, p2_input)
                
                print(f"Launching {game_file}...")
                game_path = os.path.join("src", "games", game_file)
                env = os.environ.copy()
                env["PYTHONPATH"] = os.getcwd()
                try:
                    subprocess.run([sys.executable, game_path, p1_input, p2_input], env=env)
                finally:
                    for proc in trackers:
                        proc.terminate()
                
                # Re-Initialize Curses gracefully returning from the external process
                stdscr = curses.initscr()
                curses.noecho()
                curses.cbreak()
                stdscr.keypad(True)
                curses.curs_set(0)
                curses.start_color()
                curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
                curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)

if __name__ == "__main__":
    import locale
    locale.setlocale(locale.LC_ALL, '')
    curses.wrapper(main)
