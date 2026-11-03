# Відтворення матеріалів

З каталогу lab8:

```powershell
python -m pip install -r requirements-docs.txt
python tools/build_report.py
```

Скрипт використовує Markdown, джерела діаграм і вимірювання з verification/.
Якщо локальні прогони ще не виконано, використовуються включені
docs/evidence/. Для кирилиці потрібен Arial (Windows) або DejaVu Sans (Linux).

`build_slides.mjs` — необов'язковий генератор для bundled runtime Codex:
потрібні змінні RUNTIME_NODE_MODULES, RUNTIME_PYTHON,
PRESENTATIONS_SKILL_DIR з відповідних шляхів runtime.
Звичайний запуск застосунку цих залежностей не потребує.
Готовий PPTX редагується без генератора, діаграми й графік є нативними.
