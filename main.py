import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.6-flash"  # keep the model name you already use

chat = client.chats.create(model=MODEL)

print("Pixu is ready. Type 'exit' to quit.")

while True:
    user_input = input("You: ").strip()
    if not user_input:
        continue
    if user_input.lower() in ("exit", "quit"):
        print("Pixu: Bye!")
        break
    try:
        response = chat.send_message(user_input)
        print(f"Pixu: {response.text}\n")
    except Exception as error:
        print(f"Error: {error}\n")