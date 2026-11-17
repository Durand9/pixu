import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI

load_dotenv()

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=60000),  # 60 seconds, in ms
)
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    timeout=60,
)

# Model names change over time. If one gives a 404 error, see the tip below.
MODELS = {
    "fast": {
        "label": "Llama 3.3 70B (Groq)",
        "provider": "groq",
        "name": "llama-3.3-70b-versatile",
    },
    "reasoning": {
        "label": "GPT-OSS 120B (Groq)",
        "provider": "groq",
        "name": "openai/gpt-oss-120b",
    },
    "gemini": {
        "label": "Gemini 3.6 Flash",
        "provider": "gemini",
        "name": "gemini-3.6-flash",
    },
}

# Which models to try, in order, for each type of question
ROUTES = {
    "simple": ["fast", "gemini", "reasoning"],
    "reasoning": ["reasoning", "gemini", "fast"],
}

REASONING_HINTS = [
    "calculate", "calcul", "solve", "résous", "resous", "prove", "démontre",
    "equation", "équation", "integral", "intégrale", "derivative", "dérivée",
    "sum of", "somme", "matrix", "matrice", "algorithm", "debug", "code",
]


def choose_route(question):
    q = question.lower()
    has_math = any(c.isdigit() for c in q) and any(c in q for c in "+-*/^=")
    if len(q) > 200 or has_math or any(hint in q for hint in REASONING_HINTS):
        return "reasoning"
    return "simple"


def stream_groq(model_name, messages):
    stream = groq_client.chat.completions.create(
        model=model_name, messages=messages, stream=True
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def stream_gemini(model_name, messages):
    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="medium")
    )
    for chunk in gemini_client.models.generate_content_stream(
        model=model_name, contents=contents, config=config
    ):
        if chunk.text:
            yield chunk.text


STREAMERS = {"groq": stream_groq, "gemini": stream_gemini}


def stream_answer(messages, choice="auto"):
    """Yields ("model", label), ("text", chunk) or ("error", message)."""
    if choice == "auto":
        order = ROUTES[choose_route(messages[-1]["content"])]
    else:
        order = [choice] + [k for k in ROUTES["simple"] if k != choice]

    last_error = None
    for key in order:
        info = MODELS[key]
        got_text = False
        try:
            yield ("model", info["label"])
            for text in STREAMERS[info["provider"]](info["name"], messages):
                got_text = True
                yield ("text", text)
            return
        except Exception as error:
            last_error = error
            if got_text:  # part of the answer is already on screen
                yield ("error", f"Connection lost: {error}")
                return
    yield ("error", f"All models failed. Last error: {last_error}")