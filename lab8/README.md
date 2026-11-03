# FleetFlow — фінальна версія ЛР8

Фронтенд — TypeScript 7 (strict), бекенд — FastAPI + SQLite.

Єдиний проєкт, що демонструє результати всіх восьми лабораторних.
Найзручніше запускати з кореня репозиторію: `python run.py setup`, потім `python run.py start`.

Для самостійного запуску лише цієї папки використовується включена збірка TypeScript; для редагування фронтенду: `cd frontend`, `npm ci`, `npm run build`.

Запуск бекенду:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
.venv/Scripts/python.exe launch.py
```

Панель: http://127.0.0.1:8000; Fleet: http://127.0.0.1:8101/docs;
Trips: http://127.0.0.1:8102/docs. В обох Swagger UI працює кнопка Authorize.
Логіни та паролі — у `data/LOCAL_ACCOUNTS.txt`, який не входить до Git.

З кореня `lab8/` повна перевірка: `python verification/pipeline.py`,
потім `python verification/negative_pipeline.py`.
Конвеєр перевіряє актуальність JSON OpenAPI, чистоту домену, відсутність циклів,
залежності шару застосунку, coverage >=95% і p95 <=500 мс за 100 користувачів.

## Матеріали ЛР8

- [Архітектурний пакет](docs/ARCHITECTURE.md)
- [Покриття вимог восьми робіт](docs/REQUIREMENTS.md)
- [Журнал ADR](docs/adr/INDEX.md)
- [Вимірювання і перевірки](docs/evidence/)
- [Демонстрація і регламент захисту](docs/DEMO.md)
- [PDF та презентація](submission/)
- [Джерела C4](diagrams/)

Операції початку/завершення рейсу зберігаються у SQLite. Fleet атомарно
закріплює автомобіль, оновлює пробіг і записує квитанцію команди; повтор
з тим самим trip_id та параметрами безпечний. Після втрати відповіді повторіть
ту саму дію. Тимчасову різницю станів двох БД усуває повтор команди, а не
розподілена ACID-транзакція. Деталі — ADR-011.
