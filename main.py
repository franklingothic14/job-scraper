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
    # Знайти всі вакансії за посиланнями (онови селектор під актуальний HTML)
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
        # Додатково можна отримати опис із сторінки вакансії
        try:
            job_resp = requests.get(full_link, headers=HEADERS)
            job_soup = BeautifulSoup(job_resp.text, 'html.parser')
            description_tag = job_soup.find('div', {'data-at': 'job-ad-description'})
            description = description_tag.get_text(separator=' ', strip=True)[:300] if description_tag else ''
            if "design" not in description.lower() and "design" not in title.lower():
                continue
        except Exception:
            description = ''
        jobs.append({
            'title': title,
            'company': 'N/A',
            'location': 'N/A',
            'description': description,
            'link': full_link
        })
        if len(jobs) >= 5:
            break
        await asyncio.sleep(0.5)
    return jobs

def format_message(job):
    return (
        f"📝 *{job['title']}*\n"
        f"🏢 Company: {job['company']}\n"
        f"📍 Location: {job['location']}\n"
        f"💼 Work format: Remote / Office (check job link)\n"
        f"🗣 Language: English or German (check job link)\n"
        f"💰 Compensation: Not specified\n"
        f"📄 Description: {job['description']}\n"
        f"🔗 [Job link]({job['link']})"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я бот для пошуку вакансій Motion/Design на StepStone (тільки англомовна сторінка, ключове слово 'design').\n"
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

    count = 0
    for job in jobs:
        if count >= 5:
            break
        await update.message.reply_markdown(format_message(job))
        sent_links.add(job['link'])
        count += 1
        await asyncio.sleep(0.5)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.run_polling()

if __name__ == '__main__':
    main()
