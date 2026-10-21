# ЛР №4 — Рефакторинг патернами проєктування (варіант 12)

Проєкт **«Управління автопарком та маршрутами»**. Продовження ЛР №3. Стек: Python 3.12+, FastAPI, httpx, SQLite, pytest, Uvicorn. **PostgreSQL, Docker, Redis не потрібні.**

## Чотири патерни та усунені проблеми

1. **Strategy (поведінковий)** — `gateway.py` мав розгалуження щодо типу URL; маршрутизація тепер винесена в `gateway_routing.py` (`FleetRoutes`, `TripsRoutes`).
2. **Adapter (структурний)** — `FleetClient` напряму читав JSON-поля зовнішнього сервісу; тепер вони адаптуються в типізовані `VehicleAvailability` і `DriverPermission` у `trips_service/fleet_adapter.py`.
3. **Factory (породжувальний)** — `trips_service/app.py` безпосередньо створював SQLite-репозиторій та HTTP-клієнт; тепер `TripsComponentsFactory` у `trips_service/factory.py` концентрує конфігурацію та дозволяє передавати замінники.
4. **Observer (поведінковий)** — `TripsRepository.deliver_pending()` безпосередньо записував нотифікації; тепер `TripEventPublisher` сповіщає `NotificationObserver` або інших підписників без редагування самого репозиторію.

Оригінальні 10 тестів ЛР3 збережено без змін. До рефакторингу додано чотири характеризаційні тести; після нього — чотири перевірки точок розширення.

## Перевірка у Windows PowerShell

Відкрий **папку `lab4`** у VS Code, далі виконай:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe verification\demo_live.py
```

Очікувано: **18 passed** (можливі попередження сторонніх бібліотек). В експерименті `demo_live.py`: Fleet доступний → 201; Fleet вимкнено → 503; подія TripCreated залишається в outbox й обробляється незалежно.

Swagger, якщо потрібно: Fleet — `http://127.0.0.1:8101/docs`, Trips — `http://127.0.0.1:8102/docs` після окремого запуску Uvicorn аналогічно ЛР3. Для завдання №4 достатньо тестів + історії комітів.

## Коміти в існуючому репозиторії GitHub `labs`

**Важливо:** звичайне завантаження готової папки `lab4` через браузер створить **один коміт**, а методичка №4 вимагає **послідовних невеликих комітів**. Тому додатковий архів `LR4_commit_steps.zip` має етапи `00-base` … `06-docs` і скрипт `publish_lab4.ps1`. Він створює окремі справжні коміти **локально в клоні твого репозиторію**. Після цього виконай `git push`. Не запускай скрипт, якщо `lab4` вже є в репозиторії: скрипт не перезаписує наявні файли.

Рекомендована структура GitHub: `labs/lab` (ЛР2), `labs/lab3` (ЛР3), `labs/lab4` (ЛР4). Посилання стане: `https://github.com/VladyslavCh412/labs/tree/main/lab4` **після публікації**.

Заборонено викладати `.venv/`, локальні `.sqlite`/`.db`, `__pycache__/` та секрети. Файл `.gitignore` вже доданий.

## Підтвердження і межі експерименту

`verification/metrics_lr4.json` — структурні вимірювання для окремих методів; `docs/*_before.png` та `docs/*_after.png` — UML-подібні схеми порівняння. Це локальний рефакторинг; сторонні API, хмарний CI й реальне навантаження не заявляються.
