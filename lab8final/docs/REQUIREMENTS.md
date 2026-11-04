# Что показывать по лабораторным 1–8

Это карта требований к текущей версии. Пути ниже указаны от папки lab8final.
Стек: TypeScript frontend; FastAPI + SQLite backend.

| ЛР | Что требуется | Где в проекте |
| --- | --- | --- |
| 1 | Глоссарий, участники, контекст, минимум 6 сценариев для 4 атрибутов, альтернативы, 2 ADR | docs/ARCHITECTURE.md, docs/quality-scenarios.json, docs/diagrams/context.svg, docs/adr/ |
| 2 | Четыре слоя, 3–5 сущностей, 2–3 сценария, порты хранилищ, DI, чистые доменные тесты | backend/trips/api.py → use_cases.py → domain.py → storage.py; factory.py; backend/fleet/domain.py; tests/test_domain.py |
| 3 | Два сервиса со своими данными, формальные контракты, синхронное и асинхронное взаимодействие, единая точка входа, опыт отказа | backend/fleet и backend/trips; contracts/; backend/api.py; fleet_client.py; event_bridge.py и event_worker.py; tests/test_services.py; checks/live_smoke.py |
| 4 | Четыре паттерна минимум двух групп, альтернативы, тесты до изменений, история, измерения и две диаграммы классов | backend/routing.py (Strategy), backend/trips/fleet_adapter.py (Adapter), factory.py (Factory), observers.py (Observer); docs/refactoring/; docs/diagrams/patterns/; checks/pattern_metrics.py |
| 5 | Модель и владельцы данных, локальная копия, четыре стадии миграции, кеш с инвалидацией, идемпотентные события и измерения | docs/diagrams/data-model.svg; backend/fleet/migrations/; backend/fleet/cache.py; backend/trips/read_cache.py; tests/test_data.py; checks/benchmark_cache.py |
| 6 | Границы доверия, минимум шесть угроз, токен и проверка ролей у владельца, нагрузочный план, p50/p95, оптимизация и повтор | backend/auth.py; backend/config.py; tests/test_security.py; docs/diagrams/trust.svg; docs/ARCHITECTURE.md; docs/PERFORMANCE.md; checks/load_test.py |
| 7 | Аудит тестов, unit/integration/contract, две статические и одна динамическая fitness-проверка, CI и намеренное падение | docs/TEST_AUDIT.md; tests/; checks/fitness.py; checks/pipeline.py; checks/negative_pipeline.py; .github/workflows/architecture.yml в корне репозитория |
| 8 | C4: контекст, контейнеры, компоненты; полный ADR; факт/цель качества; долг и план из трёх шагов; презентация | docs/diagrams/context.svg, containers.svg, components.svg; docs/adr/; docs/ARCHITECTURE.md; docs/evidence/; docs/submission/ |

Обычная панель открыта без входа по просьбе пользователя. Требование ЛР6
проверяется в отдельном режиме FLEETFLOW_AUTH_REQUIRED=1 через API/Swagger.
Пошаговый показ — DEMO.md. Внутренние межсервисные запросы защищены в обоих режимах.

Исторические исходники в docs/refactoring/before оставлены именно для сравнения
ЛР4. Они не запускаются. Готовые PDF/слайды и старые измерения сохранены;
текущие имена файлов — FILES.md, результаты нового прогона — вывод verify.

CI находится в корне репозитория GitHub: workflows внутри вложенной папки
GitHub не запускает, поэтому дублирующая копия удалена. Для локальных проверок
достаточно одной папки lab8final, другие лабораторные не используются.

GPS, карты и внешние SMS/email не реализованы и отмечены как долг,
а не как готовые возможности. Состав команды и устный защитный ответ
автоматические проверки подтвердить не могут.
