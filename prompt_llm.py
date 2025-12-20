import os
import time
import base64
import tkinter as tk
from tkinter import filedialog
from openai import OpenAI

api_configs = {
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "cost": {"input": 0.05, "output": 0.08} # USD per 1m tokens
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "cost": {"input": 0.15, "output": 0.6} # USD per 1m tokens
    }
}

clients = {}

for api, cfg in api_configs.items():
    if not cfg["api_key"]:
        raise ValueError(f"{api.upper()}_API_KEY not found in enviroment variable.")
    
    clients[api] = OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
    )

def calculate_cost(api_config: dict, n_tokens: int, token_type: str):
    cost_per_m = api_config["cost"][token_type]
    return (cost_per_m / 1_000_000) * n_tokens



PROMPT_CONFIG = (
    "DO AS YOU ARE TOLD AND RESPOND ONLY WITH WHAT IS ASKED FROM YOU. "
    "DO NOT EXPLAIN OR SAY WHAT YOU ARE DOING (e.g. here is the..., below is..., sure here is..., etc.). "
    "DO NOT WRITE ANY SYMBOLS LIKE - OR \\n OR CHANGE LETTER FORMATTING WITH ** AND SIMILAR. "
    "YOU ARE USED IN A TEXT PROCESSING PYTHON PROGRAM SO THE TEXT SHOULD BE PLAIN. "
)

def prompt_llm(
        system_prompt: str,
        user_prompt: str,
        is_numeric: bool,
        max_len: int
        ) -> str:
    
    start_time = time.time()
    if is_numeric:
        # acknowledge parameter (no-op) to avoid unused-variable warning
        # add "respond witha a single number" to system_prompt?
        pass

    response = clients["groq"].chat.completions.create(
        model=api_configs["groq"]["model"],
        messages=[
            {
                "role": "system",
                "content": PROMPT_CONFIG + system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }   
        ],
        max_tokens=max_len//4,
        stream=False
    )
    elapsed = time.time() - start_time
    
    if response.choices:
        llm_reply = response.choices[0].message.content.strip()
        return llm_reply
    else:
        raise ValueError("No response from LLM.")
    
def img_prompt_llm(
        system_prompt: str,
        user_prompt: str,
        img_bytes: bytes, 
        max_len: int
        ) -> str:

    start_time = time.time()

    data_url = f"data:image/png;base64,{base64.b64encode(img_bytes).decode("ascii")}"

    response = clients["openai"].chat.completions.create(
        model=api_configs["openai"]["model"],
        messages=[
            {
                "role": "system",
                "content": PROMPT_CONFIG + system_prompt
            },
            {
                "role": "user",
                "content": [
                    { "type": "text", "text": user_prompt },
                    { "type": "image_url", "image_url": { "url": data_url}}
                ]
            }
        ],
        max_tokens=max_len//4
    )

    elapsed = time.time() - start_time

    if response.choices:
        llm_reply = response.choices[0].message.content.strip()
        return llm_reply
    else:
        raise ValueError("No response from LLM.")



# if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select image file",
        filetypes=[
            ("Image files", "*.png *.jpg *.jpeg *.bmp"),
            ("All files", "*.*")
        ]
    )

    if not file_path:
        raise RuntimeError("No file selected.")

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    result = img_prompt_llm(
        prompt="Is there an electrical circuit in this image?",
        img_bytes=img_bytes,
        max_len=16
    )

    print("LLM RESULT:", repr(result))
