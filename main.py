print("🚀 main.py стартував")

import os
import re
import requests
from telethon import TelegramClient, events

# ================== ENV ==================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
CHANNEL = os.environ["CHANNEL"]

LAST_POST_ID = int(os.environ.get("LAST_POST_ID", "0"))
# =========================================


# ================== HELPERS ==================
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


# ================== DETECT GRAPH ==================
def is_power_schedule(text: str) -> bool:
    t = text.lower()
    return (
        "графік" in t
        and "погодинн" in t
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
    points = sorted(set(
        [0, 1440] +
        [t for r in q51 + q61 for t in r]
    ))

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
    date = date_match.group(0) if date_match else ""

    q51 = parse_queue(text, "5.1")
    q61 = parse_queue(text, "6.1")

    if not q51 or not q61:
        return None

    intervals = build_light_intervals(q51, q61)

    lines = [
    f"Графіки відключень світла на {date}",
    ""
]


    for start, end in intervals:
        lines.append(f"{minutes_to_time(start)}–{minutes_to_time(end)}")

    return "\n".join(lines)


# ================== STATIC TEXTS ==================
def build_contacts_text():
    return (
        "📞 Внутрішні телефони\n\n"
        "701 — рецепшн\n"
        "702 — Юрій Анатолійович\n"
        "705 — Алла Григорівна\n"
        "706 — Таїсія Вікторівна\n"
        "710 — пральня\n"
        "712 — конференц-зал №1\n"
        "713 — конференц-зал №2\n"
        "714 — технік / столова\n"
        "715 — Наталія Михайлівна\n"
        "716 — конференц-зал №3\n"
        "722 — кухня"
    )


def build_help_text():
    return (
        "🤖 Допомога по боту\n\n"
        "/help — ця довідка\n"
        "/contacts — внутрішні телефони\n"
        "/wifi — Wi-Fi для персоналу\n"
        "/codes — коди доступу\n\n"
        "Бот автоматично публікує оновлені графіки відключень світла."
    )


def build_wifi_text():
    return (
        "📶 Wi-Fi для персоналу\n\n"
        "Мережа: STAFF_WIFI\n"
        "Пароль: PASSWORD"
    )


def build_codes_text():
    return (
        "🔑 Коди доступу\n\n"
        'Корпус "В" — 4141\n'
        'Корпус "С" — 4141\n'
        "Вхід для персоналу — 4444"
    )


# ================== KEYWORD REACTIONS ==================
KEYWORD_RESPONSES = {
    "рецепшн": "📞 Рецепшн — 701",
    "технік": "🔧 Технік / столова — 714",
    "столова": "🍽️ Столова / технік — 714",
    "пральня": "🧺 Пральня — 710",
    "кухня": "🍳 Кухня — 722",
    "wifi": "📶 Wi-Fi: напишіть /wifi",
    "wi-fi": "📶 Wi-Fi: напишіть /wifi",
    "телефони": "📞 Всі телефони: /contacts",
    "конференц-зали": (
        "🏢 Конференц-зали:\n"
        "№1 — 712\n"
        "№2 — 713\n"
        "№3 — 716"
    ),
}


# ================== TELETHON ==================
client = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)


@client.on(events.NewMessage(chats=CHANNEL))
async def handler(event):
    text = event.message.text or ""
    post_id = event.message.id

    print("📥 НОВИЙ ПОСТ З КАНАЛУ")
    print("ID:", post_id)
    print(text)

    send_to_group(
        "📢 НОВИЙ ПОСТ З КАНАЛУ:\n\n" + text
    )

@client.on(events.NewMessage)
async def group_handler(event):
    if event.out:
        return

    text = event.message.text or ""
    t = text.lower().strip()

    if t == "/help":
        send_to_group(build_help_text())
        return

    if t == "/contacts":
        send_to_group(build_contacts_text())
        return

    if t == "/wifi":
        send_to_group(build_wifi_text())
        return

    if t == "/codes":
        send_to_group(build_codes_text())
        return

    for keyword, response in KEYWORD_RESPONSES.items():
        if keyword in t:
            send_to_group(response)
            return


# ================== STARTUP ==================
STARTUP_MESSAGE = (
    "⚠️ Бот був офлайн.\n"
    "Якщо під час цього вийшов новий графік — перевірте канал pat_cherkasyoblenergo."
)

send_to_group(STARTUP_MESSAGE)

print("✅ Railway бот запущений і слухає канал…")
client.run_until_disconnected()

