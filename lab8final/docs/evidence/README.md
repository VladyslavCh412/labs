# Результат проверки упрощённой версии — 04.11.2026

Проверялась отдельная чистая копия только опубликованных файлов, без старой
.venv, node_modules и рабочих баз. Выполнены setup, verify и live_smoke.

- Установка Python/npm-зависимостей и строгая сборка TypeScript: успешно.
- Рабочие fleet.sqlite и trips.sqlite создаются в папке data.
- 92 функциональных теста: успешно; покрытие доменных правил — 100%.
- Статические проверки зависимостей и циклов, актуальность OpenAPI: успешно.
- Реальный HTTP: 100 клиентов, 1461 запрос, 0 ошибок, p95 219.759 мс
  при пороге 500 мс. Это результат этого компьютера, не обещание для любого ПК.
- Намеренный import sqlite3 в домене временной копии отклонён настоящим gate.
- 9 проверок реальных серверов, включая токены, рейс, повторы, события
  и отказ Fleet: успешно.

Далее сохранены пояснения к историческим измерениям. JSON с предыдущими
нагрузочными прогонами не выдаётся за новый результат. pattern-metrics.json
пересчитан по текущим исходникам; для Strategy считаются только ветвления
выбора сервиса, без несвязанных HTTP-проверок.

---

# Перевірені результати 03.11.2026

Санітизовані результати без JWT, паролів і робочих БД. `tests-summary.json`
містить digest Python-джерел, рівні тестів і виміряний час; JUnit originals
генеруються у checks/ та зберігаються в CI artifacts.

- `load-results.json`: 20 000 рейсів, baseline/optimized, 1/10/50/100/200 users.
- `stress-results.json`: ті самі дані, optimized, 300/500 users для межі NFR-1.
- `fitness.json`: окремий CI-style HTTP gate, 5000 рейсів /100 users.
- `cache-benchmark.json`: локальний repository lookup, 1000 повторень, не HTTP.
- `live-smoke.json`: справжній HTTP login/proxy/roles/lifecycle/bridge.
- `negative-pipeline.json`: exit1 на заборонений імпорт у тимчасовій копії.
- `dashboard.png`: демонстраційні дані після завершення рейсу на 25 км.

Повторення: з кореня `python run.py verify`, `python run.py benchmark`;
з lab8 — `python checks/live_smoke.py` та
`python checks/load_test.py --modes optimized --levels 300,500 --output checks/stress_results.json`.
Середовище/тривалості/помилки записані всередині JSON. Короткий loopback
benchmark не є production SLA. Невдалий baseline із timeout не приховано.
