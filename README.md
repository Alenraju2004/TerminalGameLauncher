# 🕹️ Terminal Game Launcher

A professional, high-performance terminal-based game library and accessibility engine. Launch classic arcade games or generate new ones using AI, all controlled via various accessibility-focused input methods.

![Terminal Game Launcher](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Pygame](https://img.shields.io/badge/Library-Pygame-orange)

## 🚀 Key Features

- **Professional UI**: A sleek, high-contrast curses-based terminal interface.
- **AI Game Generation**: Synthesize complete Pygame applications on-the-fly using Google's Gemini AI.
- **Accessibility First**: Support for diverse input methods:
  - 🖥️ **Keyboard**: Standard arcade controls.
  - 👁️ **Blink Tracking**: Control actions using eye blinks (OpenCV + MediaPipe).
  - 👤 **Head Tracking**: Navigate by tilting your head.
  - 🎤 **Voice Commands**: Control gameplay using natural language.
  - 🖱️ **One-Handed Mouse**: Virtual joystick mode for mouse-only users.
- **Modular Architecture**: Cleanly separated core logic, games, and tracking modules.

## 📁 Project Structure

```text
terminal-game-launcher/
├── run.py                # Main Entry Point
├── .env                  # Environment Variables (API Keys)
├── requirements.txt      # Project Dependencies
├── src/
│   ├── launcher.py       # Curses-based Menu UI
│   ├── core/             # Input handling and server logic
│   ├── modules/          # Tracking & Accessibility drivers
│   ├── games/            # Library of competitive games
│   └── assets/           # ML models and static assets
└── data/                 # Local storage for sensitive data
```

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.8 or higher.
- A webcam (for Head/Blink tracking).
- A microphone (for Voice commands).

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure AI (Optional)
To use the AI Game Creator, create a `.env` file in the root directory and add your Gemini API key:
```env
GEMINI_API_KEY=your_api_key_here
```

## 🎮 How to Play

Launch the main application by running:
```bash
python run.py
```

### Controls
- **Navigate Menu**: Use Up/Down arrow keys.
- **Select**: Press Enter.
- **Back**: Press ESC.

## 🏗️ Technical Implementation

The system utilizes a **UDP-based Input Injection** architecture. Tracking modules (OpenCV, MediaPipe, etc.) run as isolated processes to avoid Python's Global Interpreter Lock (GIL), injecting inputs into a local server that games poll in real-time. This ensures extremely low latency and high stability even with heavy ML processing.

## 📜 License

This project is licensed under the MIT License.
