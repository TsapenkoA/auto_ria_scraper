import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

SCRAPE_HOUR = int(os.getenv("SCRAPE_HOUR", 12))
SCRAPE_MINUTE = int(os.getenv("SCRAPE_MINUTE", 0))

START_URL = "https://auto.ria.com/uk/search/?search_type=1&page=0"
