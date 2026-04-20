from stem.llm import ask_model


def main() -> None:
    answer = ask_model(
        system_prompt = "You are a test assistant.",
        user_prompt = "Reply with exactly OPENAI_OK."
    )
    print(answer)


if __name__ == "__main__":
    main()