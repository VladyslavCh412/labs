# Аудит тестів ЛР8

Виміряно 03.11.2026 з JUnit XML. Час містить setup/call/teardown для кейсу; це не лише час функції.

| Рівень | Кількість | Сума часу, с | Залежності |
|---|---:|---:|---|
| architecture | 5 | 0.080 | AST та тимчасова копія джерел |
| integration | 40 | 4.300 | Тимчасова SQLite / ASGI / mock transport |
| unit | 31 | 0.063 | Немає БД/HTTP |
| contract | 9 | 0.175 | Незалежний контракт + provider або mock |

Окремо: 1 реальний HTTP performance gate (100 users, 0 errors, p95<=500 мс).
Live smoke запускає три HTTP-процеси; його 9 перевірок не додаються до кількості pytest-кейсів.

| Файл тестів | Рівні | Кількість | Час, с |
|---|---|---:|---:|
| tests.test_architecture_extensions | architecture, integration | 4 | 0.087 |
| tests.test_characterization | integration, unit | 4 | 0.050 |
| tests.test_contract | contract | 9 | 0.175 |
| tests.test_dashboard | integration | 1 | 0.268 |
| tests.test_domain | unit | 21 | 0.021 |
| tests.test_extension_points | integration, unit | 4 | 0.040 |
| tests.test_fitness | architecture | 3 | 0.068 |
| tests.test_lab3 | integration, unit | 10 | 1.333 |
| tests.test_lab5 | integration, unit | 7 | 0.386 |
| tests.test_lifecycle | integration, unit | 9 | 0.788 |
| tests.test_pagination | integration | 1 | 0.028 |
| tests.test_read_cache | integration, unit | 3 | 0.136 |
| tests.test_security | integration | 9 | 1.238 |

Баланс: доменні правила та in-memory порти перевіряються модульно; більшість boundary-кейсів — швидкі інтеграційні ASGI/SQLite, а не повні E2E. Немає потреби піднімати весь стенд для кожного правила. Піраміда не ідеальна за кількістю, але локальна функціональна suite займає кілька секунд; дорогий HTTP gate відокремлено.

Правила ЛР2 → тести: Vehicle identity/mileage/ТО → test_domain.py; Driver.can_drive → test_driver_permission; Route stops → test_route_requires_two_nonempty_stops; Trip lifecycle → test_trip_lifecycle_and_mileage і test_transition_invariants_without_database. Persistence, migration, cache/event replay → test_lab5.py. Конкуренція і відновлення двох власників → test_lifecycle.py.
