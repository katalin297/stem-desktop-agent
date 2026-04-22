import os

from dotenv import load_dotenv
from openai import OpenAI


def get_client() -> OpenAI:
    load_dotenv(override = True)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY was not found.")

    return OpenAI(api_key = api_key)


def ask_model(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o-mini"
) -> str:
    client = get_client()

    response = client.chat.completions.create(
        model = model,
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content.strip()