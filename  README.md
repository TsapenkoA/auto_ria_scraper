# AutoRia Scraper

## Опис

Цей застосунок призначений для **щоденного скрапінгу платформи AutoRia** (б/у авто).  
Збирає всі доступні дані з кожної карточки авто та зберігає їх у **PostgreSQL**.  

Особливості:
- Асинхронний скрапінг (aiohttp + BeautifulSoup)
- Збір всіх полів: `url`, `title`, `price_usd`, `odometer`, `username`, `phone_number`, `image_url`, `images_count`, `car_number`, `car_vin`, `datetime_found`
- Унікальні записи (без дублів)
- Щоденний дамп бази у папку `dumps`
- Конфігурація через `.env`
- Запуск через Docker + docker-compose

---

### Побудувати та запустити Docker-контейнери:


`docker-compose up --build`


### Встановити залежності (якщо запускаєте локально без Docker):

`python -m venv .venv`

`source .venv/bin/activate  # Linux/Mac`

`.venv\Scripts\activate     # Windows`

`pip install -r requirements.txt`

### Використання

Для запуску скрапінгу вручну:

`python parser.py`


Для щоденного автоматичного запуску використовується scheduler.py (APScheduler):

- Збирає дані щодня о SCRAP_TIME

- Робить дамп бази о DUMP_TIME у папку dumps

Дамп бази PostgreSQL зберігається як SQL файл у:

`dumps/YYYY-MM-DD_HH-MM-SS.sql`
