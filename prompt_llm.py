import os
import time
import base64
import tkinter as tk
from tkinter import filedialog
from typing import Literal
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
        model="llama-3.1-8b-instant",
        cost={"input": 0.05, "output": 0.08}
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
        use_prompt_config: bool = True,
        max_len: int,
        ) -> str:
    
    if response_type not in ("text", "number", "text_list", "number_list"):
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
        max_tokens=max_len//4,
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

    print(f"Response took {int(elapsed)} seconds, and cost around {input_cost + output_cost:.6f} USD.")

    if response_type == "number":
        return_type = float if "." in llm_reply else int
        return return_type(llm_reply.strip())
    elif response_type in ("number_list", "text_list"):
        return_type = int if response_type == "number_list" else str
        return [return_type(num.strip().upper()) for num in llm_reply.split(",")]
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
        system_prompt="Write all text found in this image.",
        user_prompt="",
        image_bytes=img_bytes,
        response_type="text",
        max_len=200
    )

    print("LLM RESULT:", repr(result))
