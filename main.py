import os
import re
import requests
from telethon import TelegramClient, events

# ===== ENV =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
CHANNEL = os.environ["CHANNEL"]
# ===============

KEY_PHRASE = "графіки погодинних вимкнень"


def send_to_group(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })


def time_to_minutes(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def parse_queue(text: str, queue: str):
    """
    Повертає список [(start_min, end_min)] для черги
    """
    pattern = rf"{queue}\s*((?:\d{{2}}:\d{{2}}\s*-\s*\d{{2}}:\d{{2}}[, ]*)+)"
    match = re.search(pattern, text)
    if not match:
        return []

    ranges = []
    for start, end in re.findall(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})", match.group(1)):
        ranges.append((time_to_minutes(start), time_to_minutes(end)))
    return ranges


def is_off(ranges, minute):
    for start, end in ranges:
        if start <= minute < end:
            return True
    return False


def build_light_intervals(q51, q61):
    points = sorted(set(
        [0, 1440] +
        [t for r in q51 + q61 for t in r]
    ))

    light_intervals = []

    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        if not (is_off(q51, a) and is_off(q61, a)):
            light_intervals.append((a, b))

    # склеюємо
    merged = []
    for start, end in light_intervals:
        if not merged or merged[-1][1] != start:
            merged.append([start, end])
        else:
            merged[-1][1] = end

    return merged


def extract_and_build(text: str):
    if KEY_PHRASE not in text.lower():
        return None

    date_match = re.search(r"\d{1,2}\s+[а-яіїє]+", text, re.IGNORECASE)
    date = date_match.group(0) if date_match else ""

    q51 = parse_queue(text, "5.1")
    q61 = parse_queue(text, "6.1")

    if not q51 or not q61:
        return None

    intervals = build_light_intervals(q51, q61)

    lines = [
        f"Графіки погодинних вимкнень на {date}",
        "",
        "Згідно двох черг, світла не буде в такі проміжки часу:",
        ""
    ]

    for start, end in intervals:
        lines.append(f"{minutes_to_time(start)}–{minutes_to_time(end)}")

    return "\n".join(lines)


client = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)


@client.on(events.NewMessage(chats=CHANNEL))
async def handler(event):
    text = event.message.text or ""
    result = extract_and_build(text)
    if result:
        send_to_group(result)


print("✅ Чапа бот запущений і слухає канал…")
client.run_until_disconnected()
