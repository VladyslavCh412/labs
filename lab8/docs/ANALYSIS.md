# Аналіз попередніх лабораторних робіт

Дата аналізу: 27.10.2026. Джерела: актуальні `Downloads/lab1.docx`–`lab5.docx`, вісім наданих PDF-методичок, `C:/lab`, `C:/lab3`, `C:/lab4`, `C:/lab5` та публічний репозиторій https://github.com/VladyslavCh412/labs . Ранні файли `Лабораторна_робота_*_Варіант_12.docx` не використані як актуальна версія рішень, оскільки `lab1.docx` уже узгоджує FastAPI/SQLite.

| Робота | Фактичний результат | Що збережено у продовженні |
|---|---|---|
| 1 | Варіант 12; 15 термінів; 8 сценаріїв якості; ADR-001 модульний моноліт, ADR-002 FastAPI/SQLite | Ціль першої сторінки 50 активних рейсів, p95 ≤500 мс при 100 users; усі 8 NFR зі статусами |
| 2 | Чотири шари, Vehicle/Driver/Route/Trip, незалежні доменні правила | Домени не імпортують HTTP/SQLite; правила початку, завершення, допуску й ТО перевірені без БД |
| 3 | Fleet/Trips, HTTP timeout 0.35 с, контракти, TripCreated, ADR-003 | Межі сервісів і даних, HTTP 503 при відмові та outbox |
| 4 | Strategy, Adapter, Factory, Observer; характеризаційні тести | Поточні точки розширення та попередні твердження тестів |
| 5 | Незалежні SQLite, 4 SQL-міграції, cache TTL 30 с, VehicleStatusChanged, idempotent snapshot, Dashboard | Власники сутностей, версійність, cache invalidate, реальний HTTP bridge |

До змін `C:/lab5` перевірено командою `python -m pytest -q` з правильної робочої папки: 26 passed за 2.81 с. Запуск з іншої папки не знаходить історичні відносні контракти — тому інструкції вказують root проєкту.

## Виявлені прогалини

1. ЛР5 не мала автентифікації та прав; доступ через прямі порти не був захищений. ЛР6 додає JWT/RBAC саме в ресурсних API.
2. Список рейсів завантажував усю таблицю. ЛР6 додає обмежену SQL-проєкцію і відтворюване HTTP-порівняння.
3. Частина методів життєвого циклу ЛР2 після декомпозиції була відсутня в доменах ЛР5. У ЛР7 відновлено чисті доменні методи та тести; HTTP start/complete і збереження mileage окремою міграцією не заявляються.
4. Читання OpenAPI YAML у тесті саме по собі не перевіряло provider/consumer. ЛР7 додає незалежний контракт очікувань і перевіряє обидві сторони.
5. Не було обов’язкового конвеєра статичних і динамічних fitness-функцій. ЛР7 додає pipeline і негативний експеримент.
6. GPS, маршрутизація зовнішнім API, адміністрування ролей, резервне відновлення й 10-хвилинний outage не реалізовані. У ЛР8 вони явно позначені як непідтверджені, а не як завершені функції.

## Відповідність новим завданням

| Вимога | Реалізація | Доказ |
|---|---|---|
| ЛР6 межі та ≥6 загроз | Звіт ЛР6, 8 STRIDE-загроз | Модель загроз у PDF, trust diagram |
| ЛР6 login, expiry, claims | security.py, setup_local.py, Dashboard /auth/token | tests/test_security.py, live_smoke.json |
| ЛР6 права у власника, ≥2 ролі | install_security у Fleet і Trips | Прямий PATCH dispatcher →403; manager →200 |
| ЛР6 load до/після і bottleneck | verification/load_test.py; trips_service/repository.py | load_results.json, Server-Timing, test_pagination.py |
| ЛР7 бізнес-правила та SQLite | tests/test_domain.py, історичні tests/test_lab5.py | test_results.xml, coverage.json |
| ЛР7 контракт | contracts/fleet_consumer.json, tests/test_contract.py | Provider/consumer незалежні, schema mutation падає |
| ЛР7 2 статичні + 1 динамічна fitness | verification/fitness.py, tests/test_fitness.py | 0 імпортів/циклів; p95 ≤500 мс |
| ЛР7 CI і негативний дослід | verification/pipeline.py, .github/workflows/architecture.yml | pipeline.log; negative_pipeline.log, exit 1 |
| ЛР8 C4 L1/L2/L3, ADR, NFR, борг, 3 кроки | Звіт ЛР8, docs/adr/, diagrams/ | PDF, PPTX та редаговані джерела діаграм |

Нові проєкти та архіви створені окремо; попередні вихідні каталоги і GitHub не змінювались.
