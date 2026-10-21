# Автопарк та маршрути — варіант 12

## Лабораторна №2: FastAPI + SQLite

Обраний в ADR-002 (ЛР1) стек: **Python 3.12 + FastAPI + SQLite**. Доменні сутності `Vehicle`, `Driver`, `Route`, `Trip` не залежать від FastAPI або SQLite. `FleetUseCases` реалізує сценарії, репозиторії в `fleet/infrastructure` зберігають сутності, а `fleet/presentation/api.py` виконує HTTP-перетворення та валідацію. `fleet/container.py` створює конкретні залежності.

### Запуск (Windows / VS Code)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Після запуску відкрити **http://127.0.0.1:8000/docs**.

Початкові навчальні дані: автомобіль `v-1` (`BH1234AA`), водій `d-1`, маршрут `r-1` (`Одеса → Миколаїв`). Облік автомобілів і рейсів у файлі `data/fleet.sqlite` (файл створюється автоматично, Git ігнорує локальну БД).

Послідовність в `/docs`:
1. `POST /trips` → `{"id":"t-1","vehicle_id":"v-1","driver_id":"d-1","route_id":"r-1"}` → 201, `planned`.
2. `POST /trips/t-1/start` → 200, `active`.
3. `POST /trips/t-1/complete` → `{"distance_km":25}` → 200, `completed`.
4. `GET /vehicles/v-1` → `mileage_km:25`, `status:available`.
5. `GET /trips/t-1` → `completed`. Після перезапуску сервера дані залишаються в SQLite.

Після попередньої демонстрації використайте нове id, наприклад `t-2`, щоб не отримати 409. Повний скид навчальних даних: видалити `data/fleet.sqlite` при зупиненому сервері, далі повторно запустити.

### Безпека та обмеження

* ЛР2 не містить авторизації; контроль доступу — окреме завдання ЛР6. Не виставляти сервер у публічний інтернет.
* Драйвери та маршрути для ЛР2 — навчальні фікстури в пам'яті, автомобілі й рейси — SQLite.
* Сервіси ЛР3–ЛР8 в каталозі `services/` збережені як **попередній навчальний прототип**; їхній перехід на FastAPI та повна узгодженість зі стеком — окрема наступна робота.
* CI запускає набір `pytest`; GitHub Actions потрібно дійсно запустити після публікації репозиторію.
