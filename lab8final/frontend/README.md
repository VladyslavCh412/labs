# FleetFlow frontend — TypeScript

Исходный код: `src/app.ts`. TypeScript 7.0.2, `strict: true`, `noEmitOnError: true`.
Типы описывают DTO Fleet/Trips, состояние панели, роли, ответы авторизации,
проекции событий и универсальный HTTP-клиент. В исходнике нет `any`.

```powershell
npm ci
npm run typecheck
npm run build
```

Сборка создаёт `build/app.js` и копирует `styles.css` в `build/`.
FastAPI раздаёт только содержимое `build/`; исходники и node_modules
не доступны через `/assets`. `index.html` подключает скомпилированный ES-модуль.
Рабочая сборка включена в Git для автономного запуска. Редактировать следует
TypeScript-исходник, затем пересобирать; `build/app.js` вручную не редактируется.

Из корня проекта `python run.py setup` устанавливает Python/npm-зависимости
и собирает фронтенд. `start`, `test`, `verify` также запускают строгую сборку.
CI собирает TypeScript перед Python-тестами.
