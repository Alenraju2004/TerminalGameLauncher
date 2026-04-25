import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to sys.path to allow imports from src
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# Set PYTHONPATH environment variable for subprocesses
os.environ["PYTHONPATH"] = project_root

if __name__ == "__main__":
    from src.launcher import main
    import curses
    import locale
    
    locale.setlocale(locale.LC_ALL, '')
    curses.wrapper(main)
