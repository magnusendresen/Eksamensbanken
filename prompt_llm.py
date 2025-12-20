import os
import time
import base64
import tkinter as tk
from tkinter import filedialog
from typing import Literal
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

def prompt_llm(
        system_prompt: str,
        user_prompt: str,
        *,
        response_type: Literal["text", "number", "numbers"] = "text",
        image_bytes: bytes | None = None,
        use_prompt_config: bool = True,
        max_len: int,
        ) -> str:
    
    if response_type not in ("text", "number", "numbers"):
        raise ValueError(f"Invalid response_type: {response_type}")
    
    start_time = time.time()

    if use_prompt_config:
        system_prompt += (
            "DO AS YOU ARE TOLD AND RESPOND ONLY WITH WHAT IS ASKED FROM YOU. "
            "DO NOT EXPLAIN OR SAY WHAT YOU ARE DOING (e.g. here is the..., below is..., sure here is..., etc.). "
            "DO NOT WRITE ANY SYMBOLS LIKE - OR \\n OR CHANGE LETTER FORMATTING WITH ** AND SIMILAR. "
            "YOU ARE USED IN A TEXT PROCESSING PYTHON PROGRAM SO THE TEXT SHOULD BE PLAIN. "
        )

    if response_type == "number":
        system_prompt += "RESPOND WITH A SINGLE NUMBER. NO QUOTATION MARKS. NO COMMAS. NO LISTS. "
    elif response_type == "numbers":
        system_prompt += "RESPOND WITH A LIST OF NUMBERS SEPARATED BY A COMMA. NOTHING ELSE. "

    provider  = ""
    if image_bytes is None:
        provider = "groq"
        user_content = user_prompt
    else:
        provider = "openai"
        data_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"
        user_content = [
                    { "type": "text", "text": user_prompt },
                    { "type": "image_url", "image_url": { "url": data_url}}
                ]

    response = clients[provider].chat.completions.create(
        model=api_configs[provider]["model"],
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_content
            }   
        ],
        max_tokens=max_len//4,
        stream=False
    )

    if not response.choices:
        raise ValueError("No response from LLM.")
    
    llm_reply = response.choices[0].message.content.strip()

    cfg = api_configs[provider]

    input_cost = calculate_cost(api_config=cfg, n_tokens=((len(system_prompt) + len(user_prompt))//4), token_type="input")
    output_cost = calculate_cost(api_config=cfg, n_tokens=(len(llm_reply)//4), token_type="output")
    output_cost = 0
    if image_bytes is not None:
        output_cost = calculate_cost(api_config=cfg, n_tokens=int(len(base64.b64encode(image_bytes)) / 1000), token_type="input")

    elapsed = time.time() - start_time 

    print(f"Response took {int(elapsed)} seconds, and cost around {input_cost + output_cost:.6f} USD.")

    if response_type == "number":
        return float(llm_reply) if "." in llm_reply else int(llm_reply)
    elif response_type == "numbers": # Merk at numbers foreloepig kun tar Int
        return [int(num.strip()) for num in llm_reply.split(",")]
    else:
        return llm_reply
    


if __name__ == "__main__":
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

    result = prompt_llm(
        system_prompt="Is there an electrical circuit in this image? Answel with a boolean.",
        user_prompt="",
        image_bytes=img_bytes,
        response_type="number",
        max_len=16
    )

    print("LLM RESULT:", repr(result))
