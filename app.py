import os
import threading
import time
import tkinter as tk
from tkinter import scrolledtext

import pystray
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image, ImageDraw
from pynput import keyboard

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.6-flash"  # keep the model name you already use
chat = client.chats.create(
    model=MODEL,
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="medium")
    ),
)


def add_message(sender, text):
    history.config(state=tk.NORMAL)
    history.insert(tk.END, f"{sender}: {text}\n\n")
    history.config(state=tk.DISABLED)
    history.see(tk.END)


def start_reply():
    history.config(state=tk.NORMAL)
    history.insert(tk.END, "Pixu: ")
    history.config(state=tk.DISABLED)


def append_text(text):
    history.config(state=tk.NORMAL)
    history.insert(tk.END, text)
    history.config(state=tk.DISABLED)
    history.see(tk.END)


def end_reply():
    history.config(state=tk.NORMAL)
    history.insert(tk.END, "\n\n")
    history.config(state=tk.DISABLED)
    history.see(tk.END)
    send_button.config(state=tk.NORMAL)
    entry.config(state=tk.NORMAL)
    entry.focus()


def ask_ai(question):
    # Runs in a background thread so the window never freezes
    root.after(0, start_reply)
    got_text = False
    for attempt in range(3):
        try:
            for chunk in chat.send_message_stream(question):
                if chunk.text:
                    got_text = True
                    root.after(0, lambda t=chunk.text: append_text(t))
            break
        except Exception as error:
            # Retry on overload, but only if nothing was displayed yet
            if "503" in str(error) and not got_text and attempt < 2:
                time.sleep(2 * (attempt + 1))  # wait 2s, then 4s, then retry
                continue
            root.after(0, lambda e=error: append_text(f"Error: {e}"))
            break
    root.after(0, end_reply)


def send(event=None):
    question = entry.get().strip()
    if not question:
        return
    entry.delete(0, tk.END)
    add_message("You", question)
    send_button.config(state=tk.DISABLED)
    entry.config(state=tk.DISABLED)
    threading.Thread(target=ask_ai, args=(question,), daemon=True).start()


root = tk.Tk()
root.title("Pixu")
root.geometry("480x600")

history = scrolledtext.ScrolledText(
    root, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 11)
)
history.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

bottom = tk.Frame(root)
bottom.pack(fill=tk.X, padx=8, pady=(0, 8))

entry = tk.Entry(bottom, font=("Segoe UI", 11))
entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
entry.bind("<Return>", send)
entry.focus()

send_button = tk.Button(bottom, text="Send", command=send)
send_button.pack(side=tk.RIGHT, padx=(6, 0))


def show_window():
    root.deiconify()
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()
    entry.focus()
    root.after(200, lambda: root.attributes("-topmost", False))


def hide_window():
    root.withdraw()


def toggle_window():
    if root.state() == "withdrawn":
        show_window()
    else:
        hide_window()


def quit_app():
    hotkeys.stop()
    tray_icon.stop()
    root.destroy()


hotkeys = keyboard.GlobalHotKeys({
    "<ctrl>+<alt>+p": lambda: root.after(0, toggle_window),
    "<ctrl>+<alt>+q": lambda: root.after(0, quit_app),
})
hotkeys.start()


def create_tray_image():
    # Simple placeholder icon drawn in code (we can use a real logo later)
    image = Image.new("RGB", (64, 64), "#4f46e5")
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 10, 54, 54), fill="white")
    draw.ellipse((22, 22, 42, 42), fill="#4f46e5")
    return image


tray_menu = pystray.Menu(
    pystray.MenuItem(
        "Show / Hide Pixu",
        lambda icon, item: root.after(0, toggle_window),
        default=True,  # double-click on the icon does this
    ),
    pystray.MenuItem("Quit", lambda icon, item: root.after(0, quit_app)),
)

tray_icon = pystray.Icon("pixu", create_tray_image(), "Pixu", tray_menu)
tray_icon.run_detached()

# Clicking the X hides Pixu instead of closing it
root.protocol("WM_DELETE_WINDOW", hide_window)

add_message("Pixu", "Hi, I'm Pixu. How can I help?")

root.mainloop()