"""Lecture 01: a script that asks a bare LLM a question.

Usage:
    uv run python -m app.ask "What is LoRA?"
    uv run python -m app.ask            # Ask a course-specific question if none is supplied
    uv run python -m app.ask --temperature 1.5 "What is LoRA?"     # homework (Basic): change temperature
    AIE_MODEL=gemini-3.6-flash uv run python -m app.ask "What is LoRA?"   # homework (Basic): change model
    uv run python -m app.ask --chat                                # homework (Implementation): follow-up questions

A "bare" call with no tools. Check that, when asked about course-specific information,
it either says "I don't know" or gives a plausible general answer (which differs from the actual course).
(In Lecture 03, improve it by making an agent that can search the glossary.)
"""

import argparse

from google import genai
from google.genai import errors, types

from app.config import MODEL, api_error_message, get_api_key

# A course-specific question. The correct answer is in homework-levels in data/glossary.json
DEFAULT_QUESTION = "What are the 3 homework levels in the AIE2026 course?"

EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit"}
RESET_COMMAND = "/reset"


def make_config(temperature: float | None) -> types.GenerateContentConfig | None:
    """Generation settings. None = the model's default temperature."""
    if temperature is None:
        return None
    return types.GenerateContentConfig(temperature=temperature)


def format_usage(usage) -> str:
    """Lecture 01 exercise: turn response.usage_metadata into a one-line token count.

    input  = prompt_token_count (the question, plus the whole history in chat mode)
    output = candidates_token_count (the answer text)
    thinking = thoughts_token_count (internal reasoning; counted and billed, but not shown)
    """
    if usage is None:
        return "[tokens] not reported"

    def n(value):
        return value if value is not None else 0

    text = f"[tokens] input={n(usage.prompt_token_count)} output={n(usage.candidates_token_count)}"
    if usage.thoughts_token_count:
        text += f" thinking={usage.thoughts_token_count}"
    return text + f" total={n(usage.total_token_count)}"


def ask(question: str, temperature: float | None = None, model: str = MODEL) -> str:
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=model, contents=question, config=make_config(temperature))

    # Lecture 01 exercise: display input and output token counts from response.usage_metadata
    print(format_usage(response.usage_metadata))

    return response.text


# ---------------------------------------------------------------- homework (Implementation)
def chat_turn(client, history: list[types.Content], user_text: str,
              temperature: float | None = None, model: str = MODEL):
    """One turn of a conversation that keeps its history.

    The API is stateless: it remembers nothing between calls. To let the model see earlier turns,
    we send the WHOLE conversation (every user and model message so far) on every call,
    then append the new answer to the history. That is also why input tokens grow each turn.
    """
    history.append(types.Content(role="user", parts=[types.Part(text=user_text)]))
    try:
        response = client.models.generate_content(model=model, contents=history, config=make_config(temperature))
    except Exception:
        history.pop()  # the question was not answered: drop it so the history stays consistent
        raise
    answer = response.text or ""
    history.append(types.Content(role="model", parts=[types.Part(text=answer)]))
    return answer, response.usage_metadata


def chat(first_question: str | None, temperature: float | None, model: str = MODEL, input_fn=input) -> None:
    """Interactive loop. Empty line or 'exit' ends it; '/reset' forgets the history."""
    client = genai.Client(api_key=get_api_key())
    history: list[types.Content] = []
    print("Chat mode: ask follow-up questions. '/reset' clears the history, 'exit' or an empty line quits.\n")
    pending = first_question
    while True:
        if pending is None:
            try:
                pending = input_fn("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
        if not pending or pending.lower() in EXIT_COMMANDS:
            return
        if pending == RESET_COMMAND:
            history.clear()
            print("[history cleared]\n")
            pending = None
            continue
        try:
            answer, usage = chat_turn(client, history, pending, temperature, model)
        except errors.APIError as e:
            print(api_error_message(e.code, e.message) + "\n")
        else:
            print(f"model> {answer}")
            print(f"{format_usage(usage)} | turns in history: {len(history) // 2}\n")
        pending = None


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a bare LLM a question")
    parser.add_argument("question", nargs="?", default=None)
    parser.add_argument("--temperature", type=float, default=None,
                        help="sampling temperature (Gemini accepts 0.0-2.0). Default: the model's own default")
    parser.add_argument("--chat", action="store_true", help="keep the conversation history and ask follow-up questions")
    args = parser.parse_args()

    print(f"[model] {MODEL}" + (f" | temperature={args.temperature}" if args.temperature is not None else ""))
    if args.chat:
        chat(args.question, args.temperature)
        return

    question = args.question or DEFAULT_QUESTION
    print(f"[question] {question}\n")
    try:
        print(ask(question, args.temperature))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
