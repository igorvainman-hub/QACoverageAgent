# QA Coverage Agent

Компактный CLI-инструмент для анализа покрытия тестов по документации и генерации новых тест-кейсов в формате Jira Xray.

## Что делает
- парсит документацию из `docs/`
- сравнивает сценарии с существующими кейсами в `checklist.csv`
- находит пробелы в покрытии
- генерирует новые тест-кейсы
- добавляет их в `checklist.csv`

## Быстрый старт

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Настройте `.env`:

```env
OPENAI_API_KEY=sk-...
QA_BASE_PATH=MyProject
QA_TCID_PREFIX=QA
```

3. Скопируйте шаблон `checklist.example.csv` в `checklist.csv`:

```bash
copy checklist.example.csv checklist.csv
```

4. Запустите анализ:

```bash
python src/main.py
```

5. Чтобы обработать один документ:

```bash
python src/main.py --doc docs/auth_feature.md
```

## Требования
- Python 3.9+
- OpenAI API Key
- `checklist.csv` в корне проекта
- `docs/` с описанием функций и сценариев

## Структура
- `src/` — исходный код
- `docs/` — документы для анализа
- `checklist.csv` — Xray-совместимый список тест-кейсов
- `checklist.example.csv` — git-совместимый шаблон `checklist`
- `.state/` — служебные данные
- `tests/` — unit-тесты

## Примечание
Файл `DEVELOPMENT.md` удалён, документация сведена к этому краткому `README.md`.
