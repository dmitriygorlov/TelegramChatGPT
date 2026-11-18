# TelegramChatGPT

English, Russian and Python-assistance Telegram bot examples using the current OpenAI chat SDK.
Based on the original [fine-tuning article](https://habr.com/ru/post/712534/) and
[Python assistant article](https://habr.com/ru/post/724012/). The original dataset is preserved.

## Run

Python 3.15.2; install `pip install -r requirements.txt`.
Set `OPENAI_API_KEY`, `TG_TOKEN`, and `OPENAI_MODEL` to a chat model available to your account.
An old `davinci:ft-...` completion model cannot be used as a chat model.

Run one entry point: `python tg_bot_eng.py`, `python tg_bot_rus.py`, or
`python tg_bot_with_python.py`. Russian replies use the model's multilingual capability:
the unofficial googletrans prerelease and separate translation requests are no longer needed.
No connection is made when importing these modules.

Set `TG_ALLOWED_USER_IDS` to comma-separated numeric Telegram user IDs to restrict access.
This setting is **required** for the Python assistant; it replaces the old premium-secret-in-chat gate.
Set `BOT_USERNAME` (without @) to enable group replies only when mentioned or replied to.
Commands: `/start`, `/help`, `/clear`, `/code`. Group commands must be sent as a reply to the bot.
History is scoped to both chat and user, expires after 10 minutes (1 hour for Python assistance),
and is bounded. Prompt text and credentials are never logged.

Python output is **displayed, never executed**. The old in-process `exec`, automatic retry execution,
broadcast helper, email/finance/web-access imports, unused Flask proxy and secret logging are removed.
This is an intentional security change: no sandbox capable of safely running hostile code existed.
There is no automatic email, broadcast, file access or network tool execution.

## History and old formats

History is in memory unless `HISTORY_FILE` explicitly names a writable JSON file.
Persistence is atomic and single-process; do not share one file between bot processes.
For the old Python bot's `users.json`, explicitly run
`python migrate_history.py old-users.json new-history.json`, then set `HISTORY_FILE` to the result.
Only user/assistant messages and last code migrate, into private-chat context.
System prompts, premium flags and old group routing are deliberately not copied.
Expired history will reset on the next request. Keep private history files out of git and images.

Convert the original prompt/completion dataset offline with
`python convert_dataset.py dataset.jsonl chat-dataset.jsonl`.
Review the generated examples before any upload. Conversion does not train or call an API.
Use [current fine-tuning documentation](https://developers.openai.com/api/docs/guides/fine-tuning)
for supported models and training; the retired fine_tunes CLI instructions no longer apply.

## Validation and Docker

```sh
pip install -r requirements-dev.txt
python -m pytest -q
python -m pip check
ruff check .
docker build --target test -t telegram-test .
docker run --rm --network none --read-only --tmpfs /tmp telegram-test
docker build --target runtime -t telegram-bot .
```

Tests use mocks and no credentials. A runtime container only starts polling when explicitly run;
pass environment variables then, never during build. Live Telegram delivery and paid model responses
are not covered by offline tests.

## Migration and rollback

OpenAI 0.27.2 → 3.55.0; pyTelegramBotAPI 4.9.0 → 4.37.1.
Unused pandas 1.5.3, tiktoken 0.3.1, Flask 2.2.3, googletrans 3.1.0a0 and
the automatic-execution dependency collection are removed.
Rollback source baseline: `22edf640dbcbfd34b534cf745bf496fad4ad9a9f`.
Use a separate copy and backup history before migration; do not restore unsafe automatic execution
against real credentials. No runtime was deployed by this modernization.
