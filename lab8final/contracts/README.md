# Контракти

`fleet.secured.openapi.json` і `trips.secured.openapi.json` — provider specs профілю
`FLEETFLOW_AUTH_REQUIRED=1`. Звичайний локальний запуск не вимагає входу;
його поточний контракт доступний на `/openapi.json` кожного сервісу.
`verification/export_contracts.py` перевіряє тотожність виконуваному API.
`fleet_consumer.json` — незалежні очікування Trips щодо читання Fleet.
`lifecycle-contract.json` — команда, тайм-аут, ідемпотентність і помилки.
Історичні `.openapi.yaml` описують базовий API ЛР3 до JWT.
`trip_created.schema.json` описує подію, а Pydantic FleetStatusEvent/VehicleProjection
в актуальному OpenAPI — межу приймання VehicleStatusChanged.
