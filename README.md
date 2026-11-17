# Pixu

A lightweight AI assistant for Windows, built in Python.
Press a hotkey from anywhere, ask a question, get an answer.

## Features
- Chat window built with tkinter
- Conversation history
- Global hotkey to show/hide (`Ctrl+Alt+P`)
- Powered by the Gemini API
- Non-freezing UI thanks to background threads

## Setup
1. Clone the repo and open the folder
2. Create a virtual environment: `python -m venv .venv`
3. Activate it: `.venv\Scripts\Activate.ps1`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file containing `GEMINI_API_KEY=your_key_here`
6. Run: `python app.py`

## Roadmap
- [x] Terminal chat
- [x] Chat window
- [x] Global hotkey
- [x] Streaming answers
- [x] System tray icon
- [ ] Screenshot understanding
- [ ] Voice input
- [ ] Packaged .exe

## Status
Work in progress, built as a learning project.