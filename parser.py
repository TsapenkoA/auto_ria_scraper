import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re
import asyncpg
import os
import subprocess
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

START_URL = "https://auto.ria.com/uk/search/?search_type=1&page=0&limit=50"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "uk-UA,uk;q=0.9",
}

SCRAPE_HOUR = int(os.getenv("SCRAPE_HOUR", 12))
SCRAPE_MINUTE = int(os.getenv("SCRAPE_MINUTE", 0))

async def fetch(session, url):
    async with session.get(url, headers=HEADERS) as response:
        if response.status != 200:
            return None
        return await response.text()


def parse_search(html):
    soup = BeautifulSoup(html, "html.parser")
    autos = []
    seen = set()

    for a in soup.select("a[href*='auto_']"):
        href = a.get("href")
        if not href or href in seen:
            continue
        seen.add(href)

        url = href if href.startswith("http") else f"https://auto.ria.com{href}"
        title_words = a.get_text(strip=True).split()
        title = " ".join(title_words[1:4]) if len(title_words) > 1 else ""

        img = a.find("img")
        image_url = img.get("src") if img else None
        images_count = 1 if image_url else 0

        autos.append({
            "url": url,
            "title": title,
            "image_url": image_url,
            "images_count": images_count,
            "price_usd": 0,
            "odometer": None,
            "username": None,
            "phone_number": None,
            "car_number": None,
            "car_vin": None,
        })

    return autos


def parse_pinia(html):
    soup = BeautifulSoup(html, "html.parser")
    script_text = None
    for script in soup.find_all("script"):
        if script.string and "window.__PINIA__" in script.string:
            script_text = script.string
            break

    if not script_text:
        return {}

    start = script_text.find("window.__PINIA__ =") + len("window.__PINIA__ =")
    end = script_text.rfind("};") + 1
    pinia_raw = script_text[start:end].strip()

    try:
        data = json.loads(pinia_raw)
    except json.JSONDecodeError:
        return {}

    page = data.get("page", {})
    structures = page.get("structures", {})
    page_data = next(iter(structures.values()), {})

    result = {
        "price_usd": 0,
        "odometer": None,
        "username": None,
        "phone_number": None,
        "car_number": None,
        "car_vin": None,
    }

    vin = re.search(r"\b[A-HJ-NPR-Z0-9]{17}\b", json.dumps(page_data))
    if vin:
        result["car_vin"] = vin.group()

    for t in page_data.get("templates", []):
        if t.get("id") == "price":
            raw = t.get("component", {}).get("price")
            if raw:
                try:
                    result["price_usd"] = int(str(raw).replace(" ", "").replace("$", ""))
                except ValueError:
                    result["price_usd"] = 0

        if t.get("id") == "odometer":
            raw = t.get("component", {}).get("odometer")
            if raw:
                raw = raw.lower().replace("тис.", "").strip()
                if raw.isdigit():
                    result["odometer"] = int(raw) * 1000

        if t.get("id") == "main":
            for col in t.get("templates", []):
                for sub in col.get("templates", []):
                    if sub.get("id") == "photoSlider":
                        buttons = (
                            sub.get("component", {})
                            .get("photoSlider", {})
                            .get("callToAction", {})
                            .get("buttons", [])
                        )
                        for btn in buttons:
                            if btn.get("id") == "autoPhone":
                                params = btn.get("actionData", {}).get("params", {})
                                result["username"] = params.get("userName")
                                result["phone_number"] = params.get("phoneId")

    return result


async def init_db():
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE,
            title TEXT,
            price_usd INTEGER,
            odometer INTEGER,
            username TEXT,
            phone_number BIGINT,
            image_url TEXT,
            images_count INTEGER,
            car_number TEXT,
            car_vin TEXT,
            datetime_found TIMESTAMP
        )
    """)
    return conn


async def save_car(conn, car):
    await conn.execute("""
        INSERT INTO cars(url, title, price_usd, odometer, username, phone_number,
                         image_url, images_count, car_number, car_vin, datetime_found)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ON CONFLICT (url) DO NOTHING
    """,
    car["url"], car["title"], car["price_usd"], car["odometer"], car["username"],
    car["phone_number"], car["image_url"], car["images_count"],
    car["car_number"], car["car_vin"], car["datetime_found"])


async def fetch_all_cars(session):
    page = 0
    all_cars = []

    while True:
        url = f"https://auto.ria.com/uk/search/?search_type=1&page={page}&limit=50"
        html = await fetch(session, url)
        if not html:
            break
        cars = parse_search(html)
        if not cars:
            break
        all_cars.extend(cars)
        page += 1

    return all_cars


async def fetch_details(session, cars):
    tasks = [fetch(session, car["url"]) for car in cars]
    pages_html = await asyncio.gather(*tasks)

    for car, html in zip(cars, pages_html):
        pinia = parse_pinia(html)
        car.update(pinia)
        car["datetime_found"] = datetime.now()


def dump_db():
    os.makedirs("dumps", exist_ok=True)
    filename = f"dumps/dump_{datetime.now().strftime('%Y%m%d')}.sql"
    subprocess.run([
        "pg_dump",
        "-U", DB_USER,
        "-h", DB_HOST,
        "-F", "c",
        "-f", filename,
        DB_NAME
    ])


async def scrape():
    conn = await init_db()

    async with aiohttp.ClientSession() as session:
        cars = await fetch_all_cars(session)
        await fetch_details(session, cars)

        for car in cars:
            await save_car(conn, car)

    await conn.close()
    dump_db()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(scrape, 'cron', hour=SCRAPE_HOUR, minute=SCRAPE_MINUTE)
    scheduler.start()

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
