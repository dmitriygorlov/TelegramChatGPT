"""Conversation service. Importing never connects to any API."""
import json
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

from openai import APIError, OpenAI, RateLimitError


@dataclass
class Conversation:
    messages: list = field(default_factory=list)
    updated: float = 0
    code: str = ""


class ChatService:
    def __init__(self, client, model, language="English", code_mode=False, clock=time.time, history_file=None):
        self.client, self.model, self.clock = client, model, clock
        self.code_mode = code_mode
        self.system = f"Reply concisely in {language}."
        if code_mode:
            self.system += " Help write Python in fenced python blocks. This bot never executes code."
        self.users = OrderedDict()
        self.history_file = Path(history_file) if history_file else None
        if self.history_file and self.history_file.exists():
            saved = json.loads(self.history_file.read_text(encoding="utf-8"))
            if saved.get("version") != 1:
                raise ValueError("Unsupported history format; use migrate_history.py for legacy users.json")
            for row in saved["conversations"][-1000:]:
                self.users[tuple(row["key"])] = Conversation(**row["state"])

    def save(self):
        if not self.history_file:
            return
        from dataclasses import asdict
        payload = {"version": 1, "conversations": [
            {"key": list(key), "state": asdict(state)} for key, state in self.users.items()]}
        temporary = self.history_file.with_suffix(self.history_file.suffix + ".tmp")
        with open(temporary, "w", encoding="utf-8") as stream:
            os.chmod(temporary, 0o600)
            json.dump(payload, stream, ensure_ascii=False)
        temporary.replace(self.history_file)

    def clear(self, key):
        self.users.pop(key, None)
        self.save()

    def last_code(self, key):
        return self.users.get(key, Conversation()).code

    def ask(self, key, text):
        if not isinstance(text, str) or not text.strip() or len(text) >= 3000:
            return "Please send a non-empty text shorter than 3000 characters."
        now = self.clock()
        state = self.users.get(key, Conversation())
        if now - state.updated > (3600 if self.code_mode else 600):
            state = Conversation()
        messages = state.messages + [{"role": "user", "content": text}]
        while sum(len(m["content"]) for m in messages) > 24000 and len(messages) > 1:
            messages = messages[2:]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system}] + messages,
                max_completion_tokens=1000,
            )
            answer = response.choices[0].message.content
            if not answer or not answer.strip():
                return "The model returned no text. Please try another request."
        except RateLimitError:
            return "The model is busy or its quota is exhausted. Please try later."
        except APIError:
            return "The model service is unavailable. Please try later."
        state.messages = messages + [{"role": "assistant", "content": answer}]
        state.updated = now
        blocks = re.findall(r"```python\s*\n(.*?)```", answer, re.DOTALL)
        if blocks:
            state.code = "\n\n".join(blocks)
        self.users[key] = state
        self.users.move_to_end(key)
        while len(self.users) > 1000:
            self.users.popitem(last=False)
        self.save()
        return answer


def build_service(language="English", code_mode=False):
    model = os.environ.get("OPENAI_MODEL")
    if not model:
        raise ValueError("Set OPENAI_MODEL to an available chat model or chat fine-tune ID")
    return ChatService(OpenAI(timeout=30, max_retries=1), model, language, code_mode,
                       history_file=os.environ.get("HISTORY_FILE"))
