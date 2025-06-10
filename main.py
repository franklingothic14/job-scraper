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
    # Шукаємо всі посилання на вакансії в списку
    for a in soup.select('a.JobCardStyled_link__1Zd4Z'):  # приклад селектора для посилань вакансій
        link = a.get('href')
        if not link:
            continue
        if not link.startswith('http'):
            link = "https://www.stepstone.de" + link
        if link in sent_links:
            continue
        title = a.get_text(strip=True)
        # Для компанії і локації робимо запит на сторінку вакансії
        try:
            job_resp = requests.get(link, headers=HEADERS)
            job_soup = BeautifulSoup(job_resp.text, 'html.parser')
            company = job_soup.select_one('div.JobDetailsCompany_name__2fQ3E')  # приклад
            company = company.get_text(strip=True) if company else 'N/A'
            location = job_soup.select_one('span.JobDetailsLocation_location__1u5uK')
            location = location.get_text(strip=True) if location else 'N/A'
            description = job_soup.select_one('div.JobDetails_description__3f1nB')
            description = description.get_text(separator=' ', strip=True)[:300] if description else 'No description'
        except Exception:
            company = 'N/A'
            location = 'N/A'
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
    # На цьому сайті шукаємо вакансії за тегом <a> з класом job-title
    for a in soup.select('a.job-title'):
        link = a.get('href')
        if not link:
            continue
        if not link.startswith('http'):
            link = "https://www.arbeitsagentur.de" + link
        if link in sent_links:
            continue
        title = a.get_text(strip=True)
        # Локація
        parent = a.find_parent('div', class_='job-card')
        location = 'N/A'
        if parent:
            loc_span = parent.select_one('span.job-location')
            if loc_span:
                location = loc_span.get_text(strip=True)
        # Опис з окремої сторінки
        try:
            job_resp = requests.get(link, headers=HEADERS)
            job_soup = BeautifulSoup(job_resp.text, 'html.parser')
            description = job_soup.select_one('div.job-description')
            description = description.get_text(separator=' ', strip=True)[:300] if description else 'No description'
        except Exception:
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
