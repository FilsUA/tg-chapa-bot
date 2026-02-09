import os

print("🚀 BOT STARTED ON RAILWAY")

print("ENV CHECK:",
      bool(os.environ.get("API_ID")),
      bool(os.environ.get("API_HASH")),
      bool(os.environ.get("TG_SESSION")),
      bool(os.environ.get("BOT_TOKEN")),
      bool(os.environ.get("CHAT_ID")))

print("🚀 main.py стартував")

import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession


# ================== ENV ==================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
CHANNEL = os.environ["CHANNEL"].lstrip("@")
TG_SESSION = os.environ["TG_SESSION"]
# =========================================


# ================== TELEGRAM SEND ==================
def send_to_group(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })


# ================== TIME HELPERS ==================
def time_to_minutes(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


# ================== GRAPH DETECTION ==================
def is_power_schedule(text: str) -> bool:
    t = text.lower()
    return (
        "графік" in t
        and "погодин" in t
        and "години відсутності електропостачання" in t
    )


# ================== PARSE QUEUES ==================
def parse_queue(text: str, queue: str):
    pattern = rf"{queue}\s*((?:\d{{2}}:\d{{2}}\s*-\s*\d{{2}}:\d{{2}}[, ]*)+)"
    match = re.search(pattern, text)
    if not match:
        return []

    ranges = []
    for start, end in re.findall(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})", match.group(1)):
        ranges.append((time_to_minutes(start), time_to_minutes(end)))
    return ranges


def is_off(ranges, minute):
    return any(start <= minute < end for start, end in ranges)


def build_light_intervals(q51, q61):
    points = sorted(set([0, 1440] + [t for r in q51 + q61 for t in r]))

    intervals = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        if not (is_off(q51, a) and is_off(q61, a)):
            intervals.append((a, b))

    merged = []
    for start, end in intervals:
        if not merged or merged[-1][1] != start:
            merged.append([start, end])
        else:
            merged[-1][1] = end

    return merged


def extract_and_build(text: str):
    if not is_power_schedule(text):
        return None

    date_match = re.search(r"\d{1,2}\s+[а-яіїє]+", text, re.IGNORECASE)
    date = date_match.group(0) if date_match else "—"

    q51 = parse_queue(text, "5.1")
    q61 = parse_queue(text, "6.1")

    if not q51 or not q61:
        return None

    intervals = build_light_intervals(q51, q61)

    lines = [
        f"Графік відключення світла на {date}",
        ""
    ]

    for start, end in intervals:
        lines.append(f"✅ {minutes_to_time(start)}–{minutes_to_time(end)}")

    return "\n".join(lines)


# ================== TELETHON ==================
client = TelegramClient(
    StringSession(TG_SESSION),
    API_ID,
    API_HASH
)


@client.on(events.NewMessage(chats='@pat_cherkasyoblenergo'))
async def handler(event):
    text = event.message.text or ""
    print("📥 НОВИЙ ПОСТ З КАНАЛУ")
    print(text)

    send_to_group(
        "📢 НОВИЙ ПОСТ З КАНАЛУ:\n\n" + text
    )

    # фільтр ТІЛЬКИ по потрібному каналу
    if not event.chat or event.chat.username != CHANNEL:
        return

    text = event.message.text or ""
    print("📥 Новий пост з каналу")

    result = extract_and_build(text)
    if result:
        print("⚡ Знайдено графік — публікуємо")
        send_to_group(result)
    else:
        print("ℹ️ Пост без графіка — пропускаємо")


# ================== START ==================

async def keep_alive():
    while True:
        await asyncio.sleep(300)
        print("💓 keep alive")

async def main():
    await client.start()
    print("✅ User session запущена, слухає канал…")
    asyncio.create_task(keep_alive())
    await client.run_until_disconnected()

client.loop.run_until_complete(main())







