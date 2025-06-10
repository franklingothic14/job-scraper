import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from googletrans import Translator
import time

# Зчитуємо токен з environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

translator = Translator()

def scrape_stepstone():
    url = "https://www.stepstone.de/jobs/motion-designer/in-deutschland"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    jobs = []
    for job_card in soup.find_all('article', class_='job-card'):
        title_tag = job_card.find('h2')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link_tag = job_card.find('a', href=True)
        link = "https://www.stepstone.de" + link_tag['href'] if link_tag else ''
        company = job_card.find('div', class_='job-company').get_text(strip=True) if job_card.find('div', class_='job-company') else ''
        location = job_card.find('div', class_='job-location').get_text(strip=True) if job_card.find('div', class_='job-location') else ''
        
        description = ''
        if link:
            try:
                job_resp = requests.get(link, headers=headers)
                job_soup = BeautifulSoup(job_resp.text, 'html.parser')
                desc_tag = job_soup.find('div', class_='job-description')
                if desc_tag:
                    description = desc_tag.get_text(separator=' ', strip=True)[:300]
                time.sleep(1)
            except Exception:
                description = ''
        
        if description:
            try:
                description_en = translator.translate(description, dest='en').text
            except Exception:
                description_en = description
        else:
            description_en = 'No description available'

        work_format = "Remote / Office (check job link)"
        compensation = "Not specified"
        language_level = "English or German (check job link)"

        jobs.append({
            'title': title,
            'company': company,
            'location': location,
            'work_format': work_format,
            'compensation': compensation,
            'language_level': language_level,
            'description': description_en,
            'link': link
        })
    return jobs

def scrape_bundesagentur():
    url = "https://www.arbeitsagentur.de/jobsuche/suche?was=motion+designer&wo=Deutschland"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    jobs = []
    for job_card in soup.find_all('div', class_='job-card'):
        title_tag = job_card.find('a', class_='job-title')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = title_tag['href']
        if not link.startswith('http'):
            link = "https://www.arbeitsagentur.de" + link
        location_tag = job_card.find('span', class_='job-location')
        location = location_tag.get_text(strip=True) if location_tag else ''
        
        description = ''
        try:
            job_resp = requests.get(link, headers=headers)
            job_soup = BeautifulSoup(job_resp.text, 'html.parser')
            desc_tag = job_soup.find('div', class_='job-description')
            if desc_tag:
                description = desc_tag.get_text(separator=' ', strip=True)[:300]
            time.sleep(1)
        except Exception:
            description = ''

        if description:
            try:
                description_en = translator.translate(description, dest='en').text
            except Exception:
                description_en = description
        else:
            description_en = 'No description available'

        work_format = "Remote / Office (check job link)"
        compensation = "Not specified"
        language_level = "English or German (check job link)"

        jobs.append({
            'title': title,
            'location': location,
            'work_format': work_format,
            'compensation': compensation,
            'language_level': language_level,
            'description': description_en,
            'link': link
        })
    return jobs

def format_job_message(job):
    msg = (
        f"📝 *{job['title']}*\n"
        f"🏢 Company: {job.get('company', 'N/A')}\n"
        f"📍 Location: {job['location']}\n"
        f"💼 Work format: {job['work_format']}\n"
        f"🗣 Language level: {job['language_level']}\n"
        f"💰 Compensation: {job['compensation']}\n"
        f"📄 Description: {job['description']}\n"
        f"🔗 [Link to job]({job['link']})"
    )
    return msg

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привіт! Я бот для пошуку вакансій по моушен дизайну в Німеччині.\n"
                              "Введи /search для пошуку вакансій.")

def search_jobs(update: Update, context: CallbackContext):
    update.message.reply_text("Пошук вакансій на StepStone та Bundesagentur für Arbeit... Це може зайняти кілька секунд.")
    jobs = []
    try:
        jobs += scrape_stepstone()
    except Exception as e:
        update.message.reply_text(f"Помилка при скрейпінгу StepStone: {e}")

    try:
        jobs += scrape_bundesagentur()
    except Exception as e:
        update.message.reply_text(f"Помилка при скрейпінгу Bundesagentur: {e}")

    if not jobs:
        update.message.reply_text("Вакансії не знайдені.")
        return

    for job in jobs[:5]:
        msg = format_job_message(job)
        update.message.reply_markdown(msg)
        time.sleep(1)

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("search", search_jobs))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
