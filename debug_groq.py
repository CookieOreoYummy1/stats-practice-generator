from dotenv import load_dotenv
load_dotenv()
import os
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])
model = os.environ.get("MODEL_NAME", "llama-3.3-70b-versatile")
print("Using model:", model)

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": 'Reply with JSON: {"ok": true}'}],
    response_format={"type": "json_object"},
)
print(response.choices[0].message.content)
