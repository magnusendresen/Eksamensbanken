import os
import time
import base64
import tkinter as tk
from tkinter import filedialog
from typing import Literal
import threading
from datetime import datetime
from pathlib import Path
import time
from openai import OpenAI

class LLMProvider:
    def __init__(self, *, name: str, base_url: str, model: str, cost: dict[str, float]):
        self.name = name
        self.env_var = f"{name.upper()}_API_KEY"
        self.base_url = base_url
        self.model = model
        self.cost = cost  # USD per 1m tokens

        api_key = os.getenv(self.env_var)
        if not api_key:
            raise ValueError(f"{self.env_var} not found in enviroment variables.")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def estimate_cost(self, n_tokens, token_type: Literal["input", "output"]):
        return (self.cost[token_type] / 1_000_000) * n_tokens
        
LLM_PROVIDERS = {
    "groq": LLMProvider(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        cost={"input": 0.59, "output": 0.79}
    ),
    "openai": LLMProvider(
        name="openai",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        cost={"input": 0.15, "output": 0.6}
    )
}

def prompt_llm(
        system_prompt: str,
        user_prompt: str,
        *,
        response_type: Literal["text", "number", "text_list", "number_list"] = "text",
        image_bytes: bytes | None = None,
        alternatives: list | None = None,
        examples: list | None = None,
        use_prompt_config: bool = True,
        max_len: int,
        log_prompt: bool = False,
        ) -> str:
    
    if response_type not in ("text", "number", "text_list", "number_list"):
        raise ValueError(f"Invalid response_type: {response_type}")
    
    start_time = time.time()

    if use_prompt_config:
        system_prompt += (
            "DO AS YOU ARE TOLD AND RESPOND ONLY WITH WHAT IS ASKED FROM YOU. "
            "DO NOT EXPLAIN OR SAY WHAT YOU ARE DOING (e.g. here is the..., below is..., sure here is..., etc.). "
            "DO NOT WRITE ANY SYMBOLS LIKE \\n OR CHANGE LETTER FORMATTING WITH ** AND SIMILAR. "
            "YOU ARE USED IN A TEXT PROCESSING PYTHON PROGRAM SO THE TEXT SHOULD BE PLAIN. "
        )

    if response_type == "number":
        system_prompt += "RESPOND WITH A SINGLE NUMBER. NO QUOTATION MARKS. NO COMMAS. NO LISTS. "
    elif response_type == "number_list":
        system_prompt += "RESPOND WITH A LIST OF NUMBERS SEPARATED BY A COMMA. NOTHING ELSE. "

    if alternatives:
        enum_arr = []
        for i, item in enumerate(alternatives):
            enum_arr.append(f"{i}: {item}")
        system_prompt += (
            "HERE IS THE LIST OF NUMBERS YOU CAN CHOSE FROM AND THEIR VALUES: "
            ", ".join(enum_arr)
        )

    if examples:
        examples = ', '.join(map(str, examples))
        system_prompt += (
            f"HERE ARE SOME EXAMPLES: {examples}"
        )

    selected_provider  = ""
    if image_bytes is None:
        selected_provider = LLM_PROVIDERS["groq"]
        user_content = user_prompt
    else:
        selected_provider = LLM_PROVIDERS["openai"]
        data_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"
        user_content = [
                    { "type": "text", "text": user_prompt },
                    { "type": "image_url", "image_url": { "url": data_url}}
                ]
        
    max_tokens = max_len // 4 if max_len // 4 > 5 else 5

    response = selected_provider.client.chat.completions.create(
        model=selected_provider.model,
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
        max_tokens=max_tokens,
        stream=False
    )

    if not response.choices:
        raise ValueError("No response from LLM.")
    
    llm_reply = response.choices[0].message.content.strip()

    input_cost = selected_provider.estimate_cost(n_tokens=((len(system_prompt) + len(user_prompt))//4), token_type="input")
    if image_bytes is not None:
        input_cost += selected_provider.estimate_cost(n_tokens=int(len(base64.b64encode(image_bytes)) // 1000), token_type="input")
    output_cost = selected_provider.estimate_cost(n_tokens=(len(llm_reply)//4), token_type="output")

    elapsed = time.time() - start_time 

    if log_prompt:
        print(f"Response took {int(elapsed)} seconds, and cost around {input_cost + output_cost:.6f} USD.")
        log_prompt_to_file(system_prompt, user_content)

    if alternatives:
        return alternatives[int(llm_reply.strip())]
    if response_type == "number":
        return_type = float if "." in llm_reply else int
        return return_type(llm_reply.strip())
    elif response_type in ("number_list", "text_list"):
        return_type = int if response_type == "number_list" else str
        return [return_type(num.strip().upper()) for num in llm_reply.split(",")]
    else:
        return llm_reply

PROMPT_LOG_DIR = Path("prompt_logs")

def log_prompt_to_file(system_prompt: str, user_content: str):
    PROMPT_LOG_DIR.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = PROMPT_LOG_DIR / f"prompt_{ts}.txt"

    with open(path, "w", encoding="utf-8") as f:
        f.write("=== SYSTEM PROMPT ===\n\n")
        f.write(system_prompt.strip())
        f.write("\n\n=== USER CONTENT ===\n\n")
        f.write(user_content.strip())

    return path

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
        image_bytes = f.read()

    result = prompt_llm(
        system_prompt="Write all text found in this image.",
        user_prompt="",
        image_bytes=image_bytes,
        response_type="text",
        max_len=200
    )

    print("LLM RESULT:", repr(result))
