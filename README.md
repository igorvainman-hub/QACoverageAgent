# QA Coverage Agent

CLI-инструмент для анализа покрытия тестов по документации и генерации новых тест-кейсов в формате Jira Xray.

## Что делает
- парсит документы из папки docs/
- анализирует сценарии и сравнивает их с существующими кейсами в checklist.csv
- выявляет пробелы в покрытии
- генерирует новые тест-кейсы
- пишет результаты в checklist.csv и обновляет системное описание в .state/system_overview.md

## Быстрый старт

1. Установите зависимости:

```bash
python -m pip install -r requirements.txt
```

2. Создайте файл .env в корне проекта:

```env
OPENAI_API_KEY=sk-...
QA_BASE_PATH=MyProject
QA_TCID_PREFIX=QA
```

3. Запустите полный анализ по всем документам:

```bash
python -m src.main
```

4. Обработайте только один документ:

```bash
python -m src.main --doc docs/payment_feature.md
```

5. Выполните сухой прогон без записи новых кейсов:

```bash
python -m src.main --dry-run
```

6. Для подробного вывода:

```bash
python -m src.main --verbose
```

## Переменные окружения
- OPENAI_API_KEY — ключ OpenAI для генерации тест-кейсов
- QA_BASE_PATH — базовый путь для Test Repository Path в Xray
- QA_TCID_PREFIX — префикс TCID, например QA

## Примечания
- Приложение сохраняет состояние обработки в .state/state.json
- Если документ не изменился, он будет пропущен при следующем запуске
- При наличии неполных или некорректных сгенерированных кейсов они будут пропущены с предупреждением

## Требования
- Python 3.9+
- OpenAI API key
- папка docs/ с описанием функций и сценариев

## Структура проекта
- src/main.py — точка входа CLI
- src/agents/ — реализация агентной логики для анализа покрытия, проектирования тестов и обновления overview
- src/config.py, src/llm_client.py, src/document_parser.py, src/csv_writer.py — базовые модули
- docs/ — исходные документы для анализа
- checklist.csv — Xray-совместимый список тест-кейсов
- .state/ — служебные данные и состояние обработки
- tests/ — unit-тесты

## Проверка

```bash
py -m pytest -q
```
