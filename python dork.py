import asyncio
import logging
import os
import random
import html
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# ==================== CONFIG ====================
BOT_TOKEN = "8550427909:AAEvfOmAGXexjW4ySivEW0nFr8rCq5ik1ME"

MAX_PAGES = 5
MAX_RETRIES = 5
MAX_FILE_SIZE_MB = 45

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
]

# ==================== BOT SETUP ====================
default_properties = DefaultBotProperties(parse_mode="HTML")
bot = Bot(token=BOT_TOKEN, default=default_properties)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ==================== DORK POOL ====================
RANDOM_DORKS = [
    'inurl:admin login',
    'intitle:"index of" backup',
    'filetype:env DB_PASSWORD',
    'intext:"powered by shopify"',
    'site:github.com password',
]

# ==================== DDG SCRAPER ====================
async def scrape_ddg(dork: str) -> list[str]:
    results = []
    session = requests.Session()
    base_url = "https://duckduckgo.com/html/"

    for page in range(MAX_PAGES):
        params = {"q": dork, "s": page * 30}
        retries = 0

        while retries < MAX_RETRIES:
            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                r = session.get(base_url, params=params, headers=headers, timeout=30)

                if r.status_code != 200:
                    raise Exception(f"HTTP {r.status_code}")

                soup = BeautifulSoup(r.text, "html.parser")
                links = soup.find_all("a", class_="result__a")

                if not links:
                    results.append("\n--- NO MORE RESULTS ---")
                    return results

                for a in links:
                    title = html.escape(a.get_text(strip=True))
                    href = a.get("href", "")
                    results.append(f"{title} - {href}")
                    results.append("")

                results.append(f"\n--- PAGE {page + 1} ---\n")
                await asyncio.sleep(random.uniform(1.5, 3))
                break

            except Exception as e:
                retries += 1
                time.sleep(2 * retries)

    return results

# ==================== HARVEST ====================
async def perform_harvest(dork: str) -> list[str]:
    header = [
        "DUCKDUCKGO DORK HARVEST",
        f"Dork: {dork}",
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 50,
    ]

    results = await scrape_ddg(dork)
    lines = header + results

    filename = f"ddg_dork_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return [filename]

# ==================== COMMANDS ====================
@dp.message(Command("start", "help"))
async def cmd_start(message: Message):
    await message.answer(
        "😈 <b>DORKER (FREE)</b>\n\n"
        "/dork <code>&lt;query&gt;</code> → run dork\n"
        "/gen <code>&lt;num&gt;</code> → random dorks\n\n"
        "DuckDuckGo • No API • No Card"
    )

@dp.message(Command("dork"))
async def cmd_dork(message: Message, command: CommandObject):
    dork = command.args
    if not dork:
        await message.answer("Usage: /dork <code>&lt;query&gt;</code>")
        return

    safe = html.escape(dork)
    status = await message.answer(f"🔥 Executing <code>{safe}</code>")

    try:
        files = await perform_harvest(dork)
        await status.edit_text("💀 Done")
        for f in files:
            await message.answer_document(FSInputFile(f))
            os.remove(f)
    except Exception as e:
        await message.answer(f"Error: {e}")

@dp.message(Command("gen"))
async def cmd_gen(message: Message, command: CommandObject):
    try:
        num = int(command.args or 1)
    except:
        num = 1

    num = min(num, len(RANDOM_DORKS))
    selected = random.sample(RANDOM_DORKS, num)

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = "🔥 <b>RANDOM DORKS</b>\n\n"

    for i, d in enumerate(selected, 1):
        text += f"<code>{html.escape(d)}</code>\n"
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"Run #{i}", callback_data=f"run:{d}")
        ])

    await message.answer(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("run:"))
async def cb_run(call: types.CallbackQuery):
    dork = call.data.split(":", 1)[1]
    await call.message.answer(f"🔥 Executing <code>{html.escape(dork)}</code>")
    files = await perform_harvest(dork)
    for f in files:
        await call.message.answer_document(FSInputFile(f))
        os.remove(f)

# ==================== RUN ====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
