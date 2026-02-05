import asyncio
import os
import subprocess
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from parser import run_scraper
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, SCRAPE_HOUR, SCRAPE_MINUTE

def dump_db():
    os.makedirs("dumps", exist_ok=True)
    filename = f"dumps/dump_{datetime.now().strftime('%Y%m%d_%H%M')}.sql"
    subprocess.run([
        "pg_dump",
        "-h", DB_HOST,
        "-U", DB_USER,
        "-d", DB_NAME,
        "-f", filename
    ], env={**os.environ, "PGPASSWORD": DB_PASSWORD})
    print(f"💾 Дамп бази збережено: {filename}")

scheduler = AsyncIOScheduler()
scheduler.add_job(lambda: asyncio.run(run_scraper()), "cron", hour=SCRAPE_HOUR, minute=SCRAPE_MINUTE)
scheduler.add_job(dump_db, "cron", hour=SCRAPE_HOUR, minute=SCRAPE_MINUTE+5)
scheduler.start()

print("Scheduler запущений. Чекаємо на задачі...")
asyncio.get_event_loop().run_forever()
