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

async def fetch_jobs_stepstone():
    url = "https://www.stepstone.de/jobs/motion-designer/in-deutschland"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, 'html.parser')
    jobs = []
    for card in soup.find_all('article', class_='job-card'):
        link_tag = card.find('a', href=True)
        if not link_tag:
            continue
        link = "https://www.stepstone.de" + link_tag['href']
        if link in sent_links:
            continue
        title = card.find('h2').get_text(strip=True)
        company = card.find('div', class_='job-company')
        company = company.get_text(strip=True) if company else 'N/A'
        location = card.find('div', class_='job-location')
        location = location.get_text(strip=True) if location else 'N/A'
        # Опис беремо з сторінки вакансії
        try:
            job_resp = requests.get(link, headers=HEADERS)
            job_soup = BeautifulSoup(job_resp.text, 'html.parser')
            desc_tag = job_soup.find('div', class_='job-description')
            description = desc_tag.get_text(separator=' ', strip=True)[:300] if desc_tag else 'No description'
        except:
            description = 'No description'
        jobs.append({
            'title': title,
            'company': company,
            'location': location,
            'description': description,
            'link': link
        })
        if len(jobs) >= 5:
            break
        await asyncio.sleep(0.5)
    return jobs

async def fetch_jobs_bundesagentur():
    url = "https://www.arbeitsagentur.de/jobsuche/suche?was=motion+designer&wo=Deutschland"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, 'html.parser')
    jobs = []
    for card in soup.find_all('div', class_='job-card'):
        link_tag = card.find('a', class_='job-title', href=True)
        if not link_tag:
            continue
        link = link_tag['href']
        if not link.startswith('http'):
            link = "https://www.arbeitsagentur.de" + link
        if link in sent_links:
            continue
        title = link_tag.get_text(strip=True)
        location_tag = card.find('span', class_='job-location')
        location = location_tag.get_text(strip=True) if location_tag else 'N/A'
        try:
            job_resp = requests.get(link, headers=HEADERS)
            job_soup = BeautifulSoup(job_resp.text, 'html.parser')
            desc_tag = job_soup.find('div', class_='job-description')
            description = desc_tag.get_text(separator=' ', strip=True)[:300] if desc_tag else 'No description'
        except:
            description = 'No description'
        jobs.append({
            'title': title,
            'company': 'N/A',
            'location': location,
            'description': description,
            'link': link
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
        "Привіт! Я бот для пошуку вакансій Motion Designer у Німеччині.\n"
        "Введи /search для пошуку вакансій."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Шукаю вакансії...")
    jobs = []
    try:
        jobs += await fetch_jobs_stepstone()
    except Exception as e:
        await update.message.reply_text(f"Помилка StepStone: {e}")
    try:
        jobs += await fetch_jobs_bundesagentur()
    except Exception as e:
        await update.message.reply_text(f"Помилка Bundesagentur: {e}")

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
