from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
from openai import APIConnectionError

from bot_runtime import register_handlers
from gpt_utils import ChatService


def service(answer="Hello"):
    client = Mock()
    client.chat.completions.create.return_value = NS(choices=[NS(message=NS(content=answer))])
    return ChatService(client, "test-model", clock=lambda: 10000)


def test_history_expiry_and_clear():
    chat = service()
    assert chat.ask((1, 2), "hi") == "Hello"
    chat.ask((1, 2), "again")
    assert len(chat.client.chat.completions.create.call_args.kwargs["messages"]) == 4
    chat.clock = lambda: 11000
    chat.ask((1, 2), "expired")
    assert len(chat.client.chat.completions.create.call_args.kwargs["messages"]) == 2
    chat.clear((1, 2))
    assert not chat.users


@pytest.mark.parametrize("text", [None, "", " ", "a" * 3000])
def test_invalid_text_does_not_call_api(text):
    chat = service()
    chat.ask(1, text)
    chat.client.chat.completions.create.assert_not_called()


def test_errors_do_not_leak_or_mutate():
    import httpx2
    chat = service()
    chat.client.chat.completions.create.side_effect = APIConnectionError(request=httpx2.Request("GET", "https://example.test"))
    assert "unavailable" in chat.ask(1, "secret")
    assert not chat.users


def test_code_is_returned_never_executed(tmp_path):
    target = tmp_path / "should-not-exist"
    code = f"open({str(target)!r}, 'w').write('bad')"
    chat = service(f"```python\n{code}\n```")
    chat.ask(1, "run it")
    assert code in chat.last_code(1)
    assert not target.exists()


def test_history_is_separate_between_chats():
    chat = service()
    chat.ask((1, 42), "private")
    chat.ask((2, 42), "group")
    assert len(chat.client.chat.completions.create.call_args.kwargs["messages"]) == 2


def test_group_filter_and_long_unicode_reply():
    handlers = []
    bot = Mock()
    bot.message_handler.side_effect = lambda **kw: lambda fn: handlers.append(fn) or fn
    chat = service("😀" * 3000)
    register_handlers(bot, chat, "examplebot")
    message = NS(chat=NS(id=1, type="group"), from_user=NS(id=2), text="hello", reply_to_message=None)
    handlers[-1](message)
    chat.client.chat.completions.create.assert_not_called()
    message.text = "@examplebot hello"
    handlers[-1](message)
    assert bot.reply_to.call_count == 2
    assert all(len(c.args[1].encode("utf-16-le")) <= 8000 for c in bot.reply_to.call_args_list)

def test_persist_reload_clear_and_legacy_migration(tmp_path):
    import json

    from migrate_history import migrate
    path = tmp_path / "history.json"
    chat = service()
    chat.history_file = path
    chat.ask((5, 5), "remember")
    loaded = ChatService(chat.client, "test", history_file=path, clock=lambda: 10001)
    loaded.ask((5, 5), "follow up")
    assert len(loaded.client.chat.completions.create.call_args.kwargs["messages"]) == 4
    loaded.clear((5, 5))
    assert not json.loads(path.read_text())["conversations"]
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"5": {"history": [{"role": "system", "content": "exec"},
        {"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}],
        "last_prompt_time": 10000, "premium": True}}))
    migrated = tmp_path / "new.json"
    migrate(old, migrated)
    fresh = ChatService(chat.client, "test", history_file=migrated, clock=lambda: 10001)
    assert len(fresh.users[(5, 5)].messages) == 2
    assert not hasattr(fresh.users[(5, 5)], "premium")


def test_allowlist_blocks_api_and_replies():
    handlers = []
    bot = Mock()
    bot.message_handler.side_effect = lambda **kw: lambda fn: handlers.append(fn) or fn
    chat = service()
    register_handlers(bot, chat, allowed_users={123})
    message = NS(chat=NS(id=1, type="private"), from_user=NS(id=2), text="hi", reply_to_message=None)
    for handler in handlers:
        handler(message)
    chat.client.chat.completions.create.assert_not_called()
    bot.reply_to.assert_not_called()


def test_rate_limit_and_empty_response():
    import httpx2
    from openai import RateLimitError
    chat = service()
    response = httpx2.Response(429, request=httpx2.Request("POST", "https://example.test"))
    chat.client.chat.completions.create.side_effect = RateLimitError("secret", response=response, body=None)
    assert "quota" in chat.ask(1, "hi")
    assert not chat.users
    assert "no text" in service(None).ask(1, "hi")
