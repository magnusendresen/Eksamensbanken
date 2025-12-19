import os
import time
from openai import OpenAI

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("API key not found in environment variables.")
client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
usd_per_1m_input_tokens = 0.27
usd_per_1m_output_tokens = 1.10

PROMPT_CONFIG = (
    "DO AS YOU ARE TOLD AND RESPOND ONLY WITH WHAT IS ASKED FROM YOU. "
    "DO NOT EXPLAIN OR SAY WHAT YOU ARE DOING (e.g. here is the..., below is..., sure here is..., etc.). "
    "DO NOT WRITE ANY SYMBOLS LIKE - OR \\n OR CHANGE LETTER FORMATTING WITH ** AND SIMILAR. "
    "YOU ARE USED IN A TEXT PROCESSING PYTHON PROGRAM SO THE TEXT SHOULD BE PLAIN. "
)

def prompt_llm(
        prompt: str,
        is_numeric: bool,
        max_len: int) -> str:
    
    start_time = time.time()
    if is_numeric:
        # acknowledge parameter (no-op) to avoid unused-variable warning
        pass

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": PROMPT_CONFIG + "find the eigenvalues and eigenvectors of the following matrix. explain clearly and do it step by step: "
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=int(max_len/4),
        stream=False
    )
    elapsed = time.time() - start_time
    _ = elapsed
    print(f"LLM response time: {elapsed:.2f} seconds")
    
    if response.choices:
        llm_reply = response.choices[0].message.content.strip()
        return llm_reply
    else:
        raise ValueError("No response from LLM.")
    
if __name__ == "__main__":
    test_prompt = "A=[1 2 3, 4 5 6, 7 8 9]"
    out = prompt_llm(test_prompt, is_numeric=False, max_len=400)
    print("OUTPUT:", repr(out))
