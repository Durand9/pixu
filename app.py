import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

import pystray
from PIL import Image, ImageDraw
from pynput import keyboard

from models import MODELS, stream_answer

messages = []  # conversation history, shared by all models

CHOICES = {"Auto (Pixu decides)": "auto"}
for key, info in MODELS.items():
    CHOICES[info["label"]] = key


def add_message(sender, text):
    history.config(state=tk.NORMAL)
    history.insert(tk.END, f"{sender}: {text}\n\n")
    history.config(state=tk.DISABLED)
    history.see(tk.END)


def start_reply(label):
    history.config(state=tk.NORMAL)
    history.insert(tk.END, f"Pixu ({label}): ")
    history.config(state=tk.DISABLED)


def append_text(text):
    history.config(state=tk.NORMAL)
    history.insert(tk.END, text)
    history.config(state=tk.DISABLED)
    history.see(tk.END)


def end_reply(started):
    if started:
        append_text("\n\n")
    send_button.config(state=tk.NORMAL)
    entry.config(state=tk.NORMAL)
    entry.focus()


def ask_ai(choice):
    # Runs in a background thread so the window never freezes
    started = False
    label = ""
    full_text = ""
    for kind, value in stream_answer(messages, choice):
        if kind == "model":
            label = value
        elif kind == "text":
            if not started:
                started = True
                root.after(0, lambda l=label: start_reply(l))
            full_text += value
            root.after(0, lambda t=value: append_text(t))
        elif kind == "error":
            root.after(0, lambda m=value: add_message("Pixu", m))

    if full_text:
        messages.append({"role": "assistant", "content": full_text})
    else:
        messages.pop()  # remove the unanswered question from the history
    root.after(0, lambda: end_reply(started))


def send(event=None):
    question = entry.get().strip()
    if not question:
        return
    entry.delete(0, tk.END)
    add_message("You", question)
    messages.append({"role": "user", "content": question})
    send_button.config(state=tk.DISABLED)
    entry.config(state=tk.DISABLED)
    choice = CHOICES[selector.get()]
    threading.Thread(target=ask_ai, args=(choice,), daemon=True).start()


root = tk.Tk()
root.title("Pixu")
root.geometry("480x600")

top = tk.Frame(root)
top.pack(fill=tk.X, padx=8, pady=(8, 0))
tk.Label(top, text="Model:").pack(side=tk.LEFT)
selector = ttk.Combobox(top, values=list(CHOICES), state="readonly")
selector.set("Auto (Pixu decides)")
selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

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