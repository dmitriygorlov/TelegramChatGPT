"""Tests inject a fake bot; only run() starts polling."""
import os

import telebot

from gpt_utils import build_service


def register_handlers(bot, service, username="", allowed_users=None):
    username = username.lstrip("@").lower()

    def key(message):
        return (message.chat.id, message.from_user.id)

    def addressed(message):
        if allowed_users is not None and message.from_user.id not in allowed_users:
            return False
        if message.chat.type == "private":
            return True
        words = (message.text or "").split()
        reply = message.reply_to_message
        return bool(username and words and words[0].lower().rstrip(",:") == "@" + username) or bool(
            username and reply and reply.from_user and
            (reply.from_user.username or "").lower() == username)

    def send(message, answer):
        chunk, units = "", 0
        for character in answer:
            size = 2 if ord(character) > 0xFFFF else 1
            if units + size > 4000:
                bot.reply_to(message, chunk)
                chunk, units = "", 0
            chunk += character
            units += size
        if chunk:
            bot.reply_to(message, chunk)

    @bot.message_handler(commands=["start", "help", "clear"])
    def clear(message):
        if not addressed(message):
            return
        service.clear(key(message))
        send(message, "History cleared. Python code is displayed, never executed.")

    @bot.message_handler(commands=["code"])
    def code(message):
        if addressed(message):
            send(message, service.last_code(key(message)) or "No Python code in this conversation.")

    @bot.message_handler(content_types=["text"], func=lambda message: True)
    def respond(message):
        if not addressed(message):
            return
        text = message.text or ""
        if username and text.lower().startswith("@" + username):
            text = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) == 2 else ""
        send(message, service.ask(key(message), text))


def run(language="English", code_mode=False):
    allowed = os.environ.get("TG_ALLOWED_USER_IDS", "")
    if code_mode and not allowed:
        raise ValueError("Set TG_ALLOWED_USER_IDS for the Python assistant")
    allowed_users = {int(value.strip()) for value in allowed.split(",")} if allowed else None
    service = build_service(language, code_mode)
    bot = telebot.TeleBot(os.environ["TG_TOKEN"], threaded=False)
    register_handlers(bot, service, os.environ.get("BOT_USERNAME", ""), allowed_users)
    bot.infinity_polling(skip_pending=True, allowed_updates=["message"])
