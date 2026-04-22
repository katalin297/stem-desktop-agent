from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    load_dotenv()

    client = OpenAI()

    try:
        models = client.models.list()
        print("SUCCESS: the key can at least read models.")
        print("First few models:")
        for model in models.data[:10]:
            print("-", model.id)
    except Exception as e:
        print("FAILED:")
        print(type(e).__name__)
        print(e)


if __name__ == "__main__":
    main()