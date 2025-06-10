import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

sent_links = set()
HEADERS = {"User-Agent": "Mozilla/5.0"}

STEPSTONE_URL = "https://www.stepstone.de/jobs/motion-designer/in-deutschland?page=2&action=facet_selected%3BdetectedLanguages%3Ben&fdl=en"

async def fetch_jobs_stepstone():
    resp = requests.get(STEPSTONE_URL, headers=HEADERS)
    soup = BeautifulSoup(resp.text, 'html.parser')
    jobs = []
    for a in soup.find_all('a', href=True):
        link = a['href']
        if not link.startswith('/stellenangebote--'):
            continue
        full_link = "https://www.stepstone.de" + link
        if full_link in sent_links:
            continue
        title = a.get_text(strip=True)
        if "design" not in title.lower():
            continue
        jobs.append({
            'title': title,
            'link': full_link
        })
        if len(jobs) >= 5:
            break
        await asyncio.sleep(0.3)
    return jobs

def format_message(job):
    return f"📝 *{job['title']}*\n🔗 [Посилання]({job['link']})"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я бот для пошуку вакансій Motion/Design на StepStone.\n"
        "Введи /search для пошуку."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Шукаю вакансії...")
    jobs = []
    try:
        jobs += await fetch_jobs_stepstone()
    except Exception as e:
        await update.message.reply_text(f"Помилка StepStone: {e}")

    if not jobs:
        await update.message.reply_text("Вакансії не знайдені або всі вже були надіслані.")
        return

    for job in jobs:
        await update.message.reply_markdown(format_message(job))
        sent_links.add(job['link'])
        await asyncio.sleep(0.3)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.run_polling()

if __name__ == '__main__':
    main()
