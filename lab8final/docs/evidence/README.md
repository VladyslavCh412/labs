# Перевірені результати 03.11.2026

Санітизовані результати без JWT, паролів і робочих БД. `tests-summary.json`
містить digest Python-джерел, рівні тестів і виміряний час; JUnit originals
генеруються у verification/ та зберігаються в CI artifacts.

- `load-results.json`: 20 000 рейсів, baseline/optimized, 1/10/50/100/200 users.
- `stress-results.json`: ті самі дані, optimized, 300/500 users для межі NFR-1.
- `fitness.json`: окремий CI-style HTTP gate, 5000 рейсів /100 users.
- `cache-benchmark.json`: локальний repository lookup, 1000 повторень, не HTTP.
- `live-smoke.json`: справжній HTTP login/proxy/roles/lifecycle/bridge.
- `negative-pipeline.json`: exit1 на заборонений імпорт у тимчасовій копії.
- `dashboard.png`: демонстраційні дані після завершення рейсу на 25 км.

Повторення: з кореня `python run.py verify`, `python run.py benchmark`;
з lab8 — `python verification/live_smoke.py` та
`python verification/load_test.py --modes optimized --levels 300,500 --output verification/stress_results.json`.
Середовище/тривалості/помилки записані всередині JSON. Короткий loopback
benchmark не є production SLA. Невдалий baseline із timeout не приховано.
