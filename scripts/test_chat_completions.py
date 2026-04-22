from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    load_dotenv()
    client = OpenAI()

    try:
        response = client.chat.completions.create(
            model = "gpt-4o-mini",
            messages = [
                {"role": "user", "content": "Reply with exactly OK."}
            ]
        )
        print("SUCCESS: chat completions write access works.")
        print(response.choices[0].message.content)
    except Exception as e:
        print("FAILED:")
        print(type(e).__name__)
        print(e)


if __name__ == "__main__":
    main()