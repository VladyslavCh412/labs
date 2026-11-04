# Запуск с нуля

1. Установите Python 3.13: https://www.python.org/downloads/
   В классическом установщике включите Add python.exe to PATH.
2. Установите Node.js 24 с npm: https://nodejs.org/en/download
3. Установите VS Code: https://code.visualstudio.com/download
   Для F5 нужны расширения Python и Python Debugger от Microsoft.
4. Скачайте ZIP: https://github.com/VladyslavCh412/labs → Code → Download ZIP.
5. Распакуйте ZIP и откройте папку lab8final в VS Code.
6. Выполните `python run.py setup`. Подготовка нужна один раз и требует интернета.
7. Нажмите F5 или выполните `python run.py start`.
8. Откройте http://127.0.0.1:8000. Остановка: Shift+F5 либо Ctrl+C.

Без команд: Ctrl+Shift+P → Tasks: Run Task → FleetFlow: setup, затем F5.
Можно открыть FleetFlow.code-workspace двойным щелчком.

SQLite и TypeScript отдельно устанавливать не нужно.
Скрипт setup устанавливает зависимости из requirements.txt и package-lock.json,
собирает TypeScript и создаёт базы данных в data.
При следующих запусках setup повторять не требуется.

## Частые затруднения

| Сообщение | Что сделать |
| --- | --- |
| Python не найден | Перезапустите VS Code после установки; попробуйте `py -3.13 run.py setup`. |
| npm не найден | Установите Node.js с npm и заново откройте VS Code. |
| Invalid Python interpreter | Сначала setup, затем Python: Select Interpreter → .venv этого проекта. |
| Порты заняты | Возможно, приложение уже работает. Откройте панель или остановите предыдущий запуск. |
| run.py не найден | Открыта не та папка: нужен lab8final. |
| В браузере старая страница | Проверьте адрес и нажмите Ctrl+Shift+R. |

Не запускайте одновременно F5 и команду start. Открытая страница работает,
пока запущены серверы. Адрес 127.0.0.1 относится к текущему компьютеру;
преподавателю нужно скачать и запустить проект у себя.

Учебные данные входа для API: **admin / 123123**. Основная панель без входа.
Показ преподавателю: [DEMO.md](DEMO.md). Объяснение с нуля: [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md).
