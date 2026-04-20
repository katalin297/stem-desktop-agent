import os

from dotenv import load_dotenv
from openai import OpenAI


def get_client() -> OpenAI:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY was not found. Check .env."
        )

    return OpenAI(api_key = api_key)


def ask_model(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-5.4"
) -> str:
    client = get_client()

    response = client.responses.create(
        model = model,
        input = [
            {
                "role": "system",
                "content": [
                    {"type": "input_text", "text": system_prompt}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_prompt}
                ]
            }
        ]
    )

    return response.output_text.strip()