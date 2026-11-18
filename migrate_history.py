"""Explicit offline migration: legacy user-only history becomes private-chat history."""
import argparse
import json
from pathlib import Path


def migrate(source, destination):
    old = json.loads(Path(source).read_text(encoding="utf-8"))
    conversations = []
    for user_id, state in old.items():
        messages = [message for message in state.get("history", [])
                    if message.get("role") in ("user", "assistant")
                    and isinstance(message.get("content"), str)]
        while sum(len(m["content"]) for m in messages) > 24000:
            messages = messages[2:]
        conversations.append({"key": [int(user_id), int(user_id)], "state": {
            "messages": messages, "updated": state.get("last_prompt_time", 0),
            "code": state.get("last_code", "")}})
    with open(destination, "x", encoding="utf-8") as stream:
        json.dump({"version": 1, "conversations": conversations}, stream, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    migrate(args.source, args.destination)
