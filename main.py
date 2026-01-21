import os
import re
import requests
from telethon import TelegramClient, events

# ===== ENV ЗМІННІ (Railway Variables) =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
CHANNEL = os.environ["CHANNEL"]
# ========================================

KEY_PHRASES = [
    "Оновлений графік погодинних вимкнень",
    "застосовуватимуться графіки погодинних вимкнень"
]


def send_to_group(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })


def extract_needed_info(text: str):
    if not text:
        return None

    if not any(phrase in text for phrase in KEY_PHRASES):
        return None

    # Дата (наприклад: 12 вересня)
    date_match = re.search(r"\d{1,2}\s+[а-яіїє]+", text, re.IGNORECASE)

    # Блок 5.1
    block_match = re.search(
        r"5\.1\s*([\s\S]*?)(?:5\.2|$)",
        text
    )

    if not block_match:
        return None

    hours = block_match.group(1).strip()

    result_parts = []

    if date_match:
        result_parts.append(f"📅 {date_match.group(0)}\n")

    result_parts.append(
        "Години відсутності електропостачання:\n"
        "5.1 " + hours
    )

    return "\n".join(result_parts).strip()


client = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)


@client.on(events.NewMessage(chats=CHANNEL))
async def handler(event):
    text = event.message.text or ""
    prepared = extract_needed_info(text)
    if prepared:
        send_to_group(prepared)


print("✅ Railway бот запущений і слухає канал…")
client.run_until_disconnected()
