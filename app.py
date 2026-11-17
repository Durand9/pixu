import os
import threading
import time
import tkinter as tk
from tkinter import scrolledtext

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.8-flash"  # keep the model name you already use
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


def ask_ai(question):
    # Runs in a background thread so the window never freezes
    answer = None
    for attempt in range(3):
        try:
            answer = chat.send_message(question).text
            break
        except Exception as error:
            if "503" in str(error) and attempt < 2:
                time.sleep(2 * (attempt + 1))  # wait 2s, then 4s then retry
                continue
            answer = f"Error: {error}"
            break
    root.after(0, lambda: show_answer(answer))


def show_answer(answer):
    add_message("Pixu", answer)
    send_button.config(state=tk.NORMAL)
    entry.config(state=tk.NORMAL)
    entry.focus()


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

add_message("Pixu", "Hi, I'm Pixu. How can I help?")

root.mainloop()