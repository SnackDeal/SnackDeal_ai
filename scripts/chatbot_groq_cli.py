from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.chatbot.schema import ChatbotRequest
from src.chatbot.service import answer


def _load_env() -> None:
    for path in [PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"]:
        if path.exists():
            load_dotenv(path)
            print(f"Loaded env: {path}")
            break

    os.environ.setdefault("CHATBOT_LLM_PROVIDER", "groq")
    os.environ.setdefault("GROQ_MODEL", "llama-3.1-8b-instant")


async def _ask(message: str) -> None:
    response = await answer(ChatbotRequest(message=message))
    print(f"\nSnackDeal Bot: {response.answer}\n")


async def main() -> None:
    _load_env()

    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to "
            f"{PROJECT_ROOT / '.env'} or your shell environment."
        )

    if len(sys.argv) > 1:
        await _ask(" ".join(sys.argv[1:]))
        return

    print("SnackDeal Groq chatbot test")
    print("Type a question and press Enter. Type exit to quit.\n")

    while True:
        message = input("You: ").strip()
        if message.lower() in {"exit", "quit", "q"}:
            break
        if not message:
            continue
        await _ask(message)


if __name__ == "__main__":
    asyncio.run(main())
