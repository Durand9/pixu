import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI

from pytool import run_python

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

# Model names change over time. If one gives a 404 error, update it here.
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

MATH_PATTERN = re.compile(r"\d\s*[+*/^=×÷]\s*\d|\d\s+-\s+\d")
CALC_HINTS = [
    "calculate", "calcul", "compute", "sum of", "somme", "product of",
    "factorial", "prime", "average", "moyenne",
]
REASONING_HINTS = [
    "solve", "résous", "resous", "prove", "démontre", "equation", "équation",
    "integral", "intégrale", "derivative", "dérivée", "matrix", "matrice",
    "algorithm", "debug", "code",
]

CODE_PROMPT = (
    "Write a short Python program that computes the answer to the question "
    "below. Rules: print the final result with print(); use only 'import math' "
    "and plain Python; no input(), no files, no network. Reply with ONLY the "
    "code, no explanation.\n\nQuestion: "
)


def choose_route(question):
    q = question.lower()
    if MATH_PATTERN.search(q) or any(hint in q for hint in CALC_HINTS):
        return "math"
    if len(q) > 200 or any(hint in q for hint in REASONING_HINTS):
        return "reasoning"
    return "simple"


# ---------- streaming (answers appear word by word) ----------

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


# ---------- single answers (used to ask for Python code) ----------

def once_groq(model_name, prompt):
    response = groq_client.chat.completions.create(
        model=model_name, messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def once_gemini(model_name, prompt):
    response = gemini_client.models.generate_content(
        model=model_name, contents=prompt
    )
    return response.text


ONCE = {"groq": once_groq, "gemini": once_gemini}


def ask_once(order, prompt):
    for key in order:
        info = MODELS[key]
        try:
            return ONCE[info["provider"]](info["name"], prompt)
        except Exception:
            continue
    return None


def extract_code(text):
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def try_python(question):
    """Returns (code, output) if Python solved it, otherwise None."""
    reply = ask_once(ROUTES["reasoning"], CODE_PROMPT + question)
    if not reply:
        return None
    code = extract_code(reply)
    try:
        output = run_python(code)
    except Exception:
        return None
    if not output:
        return None
    return code, output


# ---------- main entry point used by the window ----------

def stream_answer(messages, choice="auto"):
    """Yields ("model", label), ("text", chunk) or ("error", message)."""
    if choice == "auto":
        question = messages[-1]["content"]
        route = choose_route(question)
        if route == "math":
            found = try_python(question)
            if found:
                code, output = found
                yield ("model", "Python")
                yield ("text", f"I ran this Python code:\n{code}\n\nResult: {output}\n\n")
                messages = messages[:-1] + [{
                    "role": "user",
                    "content": (
                        f"{question}\n\n(Python computed this exact result: "
                        f"{output}. Give the final answer clearly and briefly, "
                        "using this result.)"
                    ),
                }]
            order = ROUTES["reasoning"]
        else:
            order = ROUTES[route]
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