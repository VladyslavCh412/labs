# ЛР №3 — Автопарк та маршрути (варіант 12)

**Стек:** Python 3.12+ / FastAPI / SQLite / httpx / pytest. Продовження предметної області ЛР2. Не потрібні PostgreSQL, Docker, Redis.

## Структура та межі

- `fleet_service/`: власник ТЗ і водіїв, **тільки** `data/fleet.sqlite`.
- `trips_service/`: власник маршрутів, рейсів і подій, **тільки** `data/trips.sqlite`.
- `gateway.py`: єдина точка входу, не зберігає власні дані.
- `event_worker.py`: незалежний підписник `TripCreated`. Оновлює локальний журнал повідомлень у БД власника Trips. Підписник і продюсер не викликають один одного; це локальна демонстрація outbox, без зовнішнього брокера.
- `contracts/`: `fleet.openapi.yaml`, `trips.openapi.yaml` та `trip_created.schema.json` — формалізовані контракти HTTP і події; `/openapi.json` генерує FastAPI автоматично.

**Синхронний потік:** Gateway → Trips → HTTP GET Fleet (до 350 мс на кожен запит до Fleet) → Trips SQLite. При зупиненому Fleet повертається **503**, рейс не створюється (fail-closed). API `POST /trips` не слід повторювати без контролю `id`: повтор з наявним id повертає **409**.

**Асинхронний потік:** Trips у єдиній SQLite-транзакції створює рейс і `TripCreated` у outbox → незалежний worker зчитує чергу та ідемпотентно заносить повідомлення в `notification_inbox`, позначає доставлене. Якщо worker недоступний, подія зберігається; якщо Fleet зупинено *після створення рейсу*, worker все одно її обробляє. Реальний розподілений брокер не застосовується.

## Windows — підготовка

1. Розпакувати папку `lab3`, відкрити її у VS Code.
2. Запустити PowerShell у цій папці:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe verification\demo_live.py
```

`verification/demo_live.py` **сам** запускає три реальні HTTP-сервери, імітує падіння Fleet, доставляє `TripCreated` після падіння і зберігає `verification/live_demo_results.txt`. Цей журнал (і скриншот термінала) — доказ інтеграційного експерименту для звіту.

## Windows — ручна демонстрація та скріншоти

Відкрити **чотири термінали PowerShell** у папці лабораторної №3 та виконати (одна команда в одному терміналі, сервери не закривати):

**Термінал 1 — Fleet**

```powershell
.\.venv\Scripts\python.exe -m uvicorn fleet_service.app:app --port 8101
```

**Термінал 2 — Trips**

```powershell
.\.venv\Scripts\python.exe -m uvicorn trips_service.app:app --port 8102
```

**Термінал 3 — Gateway**

```powershell
.\.venv\Scripts\python.exe -m uvicorn gateway:app --port 8000
```

**Термінал 4 — worker**

```powershell
.\.venv\Scripts\python.exe -m event_worker
```

Відкрити Swagger: **http://127.0.0.1:8101/docs** (Fleet), **http://127.0.0.1:8102/docs** (Trips), **http://127.0.0.1:8000/docs** (Gateway, проксі-маршрути `/` задаються динамічно й не перелічуються як окремі операції, тому для створення рейсу зручніше користуватися Swagger Trips).

У Swagger Trips: `POST /trips` → `Try it out` → JSON:

```json
{"id":"t-manual-1","vehicle_id":"v-1","driver_id":"d-1","route_id":"r-1"}
```

Очікувано **201**, а `GET /events/outbox` покаже `TripCreated` і `delivered=true`, коли worker активний. `GET /notifications` покаже повідомлення. Якщо створений id уже існує, використовуй новий id (`t-manual-2` і т.д.) або видали `data/*.sqlite` при зупинених процесах.

**Демонстрація недоступності:** натиснути `Ctrl+C` лише в терміналі 1 (Fleet); термінали 2, 3, 4 лишаються працювати. Надіслати новий `POST /trips` з id `t-fail-1`: очікувано **503**. При цьому `GET /notifications` працює і раніше створені події не зникають. Для повторної перевірки запусти Fleet знову в терміналі 1.

**Для звіту користувач робить скриншоти:** два Swagger (Fleet і Trips), відповідь `201`, відповідь `503` після `Ctrl+C` та термінал `pytest` / інтеграційний журнал. Ці скриншоти поки не включені до початкового звіту; їх можна вставити після реального запуску на ПК.

## GitHub

Скопіювати **весь вміст цієї папки** до `labs/lab3` (поряд з уже завантаженою папкою `labs/lab`). Не завантажувати `.venv`, кеші, SQLite-файли `data/` і приватні токени. ЛР2 не видаляти. Після завантаження додати точну URL-адресу папки до звіту №3.

## Межі прототипу

Це лабораторна архітектурна демонстрація: немає автентифікації (ЛР6), унікальність бронювання авто між одночасними рейсами не гарантована без окремого механізму резервування, немає зовнішнього message broker. Подальші етапи розглядаються в ЛР5–7. Ніякі вигадані мережеві вимірювання чи CI-запуски не заявляються.
