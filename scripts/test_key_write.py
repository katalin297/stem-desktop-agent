from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    load_dotenv()

    client = OpenAI()

    try:
        response = client.responses.create(
            model = "gpt-5.4",
            input = "Reply with exactly OK."
        )
        print("SUCCESS: write access works.")
        print(response.output_text)
    except Exception as e:
        print("FAILED:")
        print(type(e).__name__)
        print(e)


if __name__ == "__main__":
    main()