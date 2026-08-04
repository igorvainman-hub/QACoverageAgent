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

3. Запустите полный анализ по всем документам через явный режим:

```bash
python -m src.main generate-docs
```

4. Обработайте только один документ через явный режим:

```bash
python -m src.main generate-docs --doc payment_feature.md
```

5. Выполните сухой прогон без записи новых кейсов:

```bash
python -m src.main generate-docs --dry-run
```

6. Для подробного вывода:

```bash
python -m src.main generate-docs --verbose
```

## Генерация API-тестов

Для автоматической генерации API-автотестов:

1. добавьте метку `api` в поле `Label` нужного кейса в `checklist.csv`;
2. передайте JSON-спецификацию OpenAPI в команду:

```bash
python -m src.main generate-tests --openapi https://service.example/v3/api-docs
python -m src.main generate-tests --openapi docs/openapi.json --output-dir automation/api
python -m src.main generate-tests --openapi docs/openapi.json --dry-run --verbose
```

Что делает режим:
- читает OpenAPI-спецификацию;
- создаёт клиентов по `tags` из спецификации;
- генерирует Playwright-спеки;
- при необходимости добавляет заготовку `fixtures/auth.ts` и `coverage-report.md`.

Ограничения:
- поддерживаются только JSON-спецификации OpenAPI; YAML сначала нужно конвертировать в JSON;
- для URL-спецификаций разрешены только публично маршрутизируемые HTTP(S)-адреса;
- loopback, private, link-local, reserved IP-адреса и redirects блокируются;
- для внутреннего API лучше сохранить JSON-файл локально и передать путь к нему;
- если API-кейсов не найдено, команда завершится успешно без создания файлов.

`generate-docs` — явный режим для генерации кейсов по одному документу:

```bash
python -m src.main generate-docs --doc payment_feature.md
```

Это отдельный CLI-режим для документационного pipeline. Он читается как "сгенерировать Xray-кейсы из одного markdown-файла" и не требует дополнительных команд для запуска.

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
- src/app/pipeline.py — отдельный pipeline обработки документа: чтение, анализ, генерация кейсов, сохранение состояния
- src/agents/ — реализация агентной логики для анализа покрытия, проектирования тестов и обновления overview
- src/config.py, src/llm_client.py, src/document_parser.py, src/csv_writer.py — базовые модули
- docs/ — исходные документы для анализа
- checklist.csv — Xray-совместимый список тест-кейсов
- .state/ — служебные данные и состояние обработки
- tests/ — unit-тесты, включая проверку pipeline

## Архитектурные принципы
- CLI отвечает только за запуск и аргументы
- обработка документа выделена в отдельный pipeline, что упрощает поддержку и развитие
- внешние зависимости (LLM, CSV, state) изолированы от основной логики

## Проверка

```bash
py -m pytest -q
```
