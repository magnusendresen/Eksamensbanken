from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("NEW_OPENAI_API_KEY"))

models = client.models.list()
for m in models.data:
    print(m.id)
