# Матриця відповідності ЛР1–ЛР8

Обов’язковий стек: TypeScript frontend (strict, npm build), FastAPI + SQLite backend.

Це навігація по коду й матеріалах ЛР8, а не окремі звіти для ЛР1–ЛР7.

| ЛР | Обов'язкова вимога | Реалізація / доказ |
|---|---|---|
| 1 | 12–15 термінів, stakeholders, контекст | ARCHITECTURE.md §§1–3, context.mmd/svg |
| 1 | >=6 сценаріїв, >=4 атрибути, 2–3 альтернативи, 2 ADR | §9: 8 вихідних сценаріїв; §4; ADR-001/002 originals |
| 2 | 4 шари, 3–5 сутностей, правила в домені | trips_service/{app,application,domain,repository}.py; Fleet Vehicle/Driver + Trips Route/Trip |
| 2 | 2–3 use cases, repo ports, DI | trips_service/{domain,application,factory}.py; create_app — composition root |
| 2 | Домени без БД, напрям залежностей | test_domain.py, test_fitness.py, test_architecture_extensions.py |
| 3 | 2–3 сервіси, власні дані, gateway | fleet_service/, trips_service/, dashboard.py; containers.mmd |
| 3 | Формальні контракти й гарантії | contracts/*.secured.openapi.json, fleet_consumer.json, lifecycle-contract.json |
| 3 | Sync timeout, async consumer, дослід відмови | fleet_client.py timeout0.35; event_bridge.py/event_worker.py; test_lab3.py/live_smoke.py |
| 4 | 4 патерни >=2 груп, alternatives, before/after | ARCHITECTURE.md §6; gateway_routing.py, fleet_adapter.py, factory.py, observers.py |
| 4 | Тести до змін, малі коміти, 2 class diagrams | test_characterization.py; docs/refactoring/history.json; diagrams/patterns/*before.dot/*after.dot; evidence/pattern-metrics.json |
| 5 | Моделі/власники й read-only копія | §7; data-model.mmd/svg; vehicle_snapshot |
| 5 | 4 стадії expand–contract | fleet_service/migrations/001..004; test_all_four_migrations_and_backward_compatibility |
| 5 | Кеш, інвалідація, вимір до/після | fleet_service/cache.py; trips_service/read_cache.py; evidence/cache-benchmark.json |
| 5 | Ідемпотентна подія, оцінка відставання | event_bridge.py; repository.apply_fleet_event; §7; test_lab5.py |
| 6 | Trust boundaries і >=6 загроз | §8: 9 загроз; trust.mmd/svg |
| 6 | Login, JWT expiry, >=2 ролі у власника | Профіль FLEETFLOW_AUTH_REQUIRED=1: security.py, setup_local.py; test_security.py, test_lifecycle.py. Звичайний запуск без входу. |
| 6 | План навантаження, p50/p95, bottleneck, повтор | §9; load_test.py; evidence/load-results.json/stress-results.json |
| 7 | Аудит/правила/інтеграція/контракти | TEST_AUDIT.md; tests/test_domain.py, test_lab5.py, test_contract.py |
| 7 | >=3 fitness, CI, навмисне падіння | fitness.py/pipeline.py/negative_pipeline.py; .github/workflows/architecture.yml |
| 8 | C4 L1/L2/L3 для одного контейнера | diagrams/context, containers, components (.mmd/.svg) |
| 8 | Повний ADR журнал зі статусами | docs/adr/INDEX.md, ADR-001–014; originals збережено |
| 8 | NFR факт/ціль, борг, 3 кроки з тригерами | ARCHITECTURE.md §§9–12; evidence/ |
| 8 | Пакет PDF, презентація <=10 хв, сценарій | submission/FleetFlow_Lab8.pdf, FleetFlow_Defense.pptx; DEMO.md |

Фактичні профілі NFR мають і невиконані пункти: карти, GPS, рольове
адміністрування, backup drill. Методичка ЛР8 вимагає показати їх стан і
борг, тому вони не позначені як реалізовані. Організаційний склад команди,
ротацію ролей і усний захист програмний проєкт не може підтвердити.

Усі наведені файлові шляхи відносні до цієї папки. Власні run.py, .vscode/, .gitignore та CI включені; сусідні папки не використовуються.

Самостійність кінцевого продукту перевірена окремою копією без інших лабораторних: [доказ](evidence/standalone.json).
