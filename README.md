# QA Coverage Agent

CLI-проект для анализа покрытия функциональности по документации, выявления пробелов и генерации готовых тест-артефактов для Xray, API-автотестов и k6 load-путей.

## Что делает проект

Проект умеет три основных сценария:

1. Генерация ручных Xray-кейсов из Markdown-документов
   - читает файлы из папки `docs/`
   - сопоставляет сценарии с текущими кейсами в `checklist.csv`
   - находит пробелы в покрытии
   - создаёт новые тест-кейсы и обновляет `.state/system_overview.md`

2. Генерация API-автотестов на Playwright
   - берёт кейсы из `checklist.csv` с меткой `api`
   - анализирует OpenAPI-спецификацию
   - создаёт клиентов по `tags`
   - генерирует спецификации под `automation/api`

3. Генерация k6 load-тестов по journey
   - принимает набор TCID в нужном порядке выполнения
   - маппит их на endpoints из OpenAPI
   - создаёт один или несколько k6-скриптов и markdown-отчётов

## Архитектура

Главные модули:

- `src/main.py` — точка входа CLI
- `src/app/pipeline.py` — pipeline обработки документа и сохранения state
- `src/agents/` — агенты для покрытия, дизайна тестов, OpenAPI и load-генерации
- `src/config.py` — загрузка runtime-конфигурации
- `src/llm_client.py` — обёртка над LLM
- `src/document_parser.py` — разбор документов
- `src/csv_writer.py` — запись и валидация Xray-кейсов

## Быстрый старт

### 1. Установка зависимостей

```bash
python -m pip install -r requirements.txt
```

### 2. Настройка окружения

Создайте файл `.env`:

```env
OPENAI_API_KEY=sk-...
QA_BASE_PATH=MyProject
QA_TCID_PREFIX=QA
```

### 3. Команды CLI

#### Генерация ручных тест-кейсов по документам

```bash
python -m src.main generate-docs
```

Или только один документ:

```bash
python -m src.main generate-docs --doc payment_feature.md
```

Сухой прогон:

```bash
python -m src.main generate-docs --dry-run
```

Подробный вывод:

```bash
python -m src.main generate-docs --verbose
```

#### Генерация API-автотестов

Чтобы генерация сработала на реальных данных, в `checklist.csv` должен быть хотя бы один кейс с меткой `API` или `Smoke;API`.

Примеры:

```bash
python -m src.main generate-tests --openapi docs/openapi.json --output-dir automation/api
python -m src.main generate-tests --openapi docs/openapi.json --dry-run --verbose
```

Что делает этот режим:

- читает OpenAPI-спецификацию
- создаёт клиентов по `tags`
- генерирует Playwright-спеки
- добавляет `fixtures/auth.ts` и `coverage-report.md` при необходимости

Ограничения:

- поддерживаются только JSON-спецификации OpenAPI
- публичные URL разрешены только для открытых HTTP(S) ресурсов
- loopback, private, link-local, reserved и redirect-адреса блокируются
- для внутреннего API лучше передавать локальный JSON-файл

#### Генерация k6 load-тестов

Команда создаёт один или несколько k6-скриптов для линейных API-journeys.

```bash
python -m src.main generate-load-tests --openapi docs/openapi.json --journey QA-API-001,QA-API-003 --base-url http://testURL --vus 150 --duration 4m --output-dir automation/load
python -m src.main generate-load-tests --openapi docs/openapi.json --journey QA-101,QA-104,QA-110
python -m src.main generate-load-tests --openapi docs/openapi.json --journey QA-101,QA-104 --thresholds k6-thresholds.json --vus 50 --duration 2m --output-dir automation/load
python -m src.main generate-load-tests --openapi docs/openapi.json --journey QA-101,QA-104 --journey QA-201,QA-220
```

Правила:

- TCID должны уже существовать в `checklist.csv`
- порядок TCID должен быть точным порядком выполнения
- каждый `--journey` создаёт независимый сценарий
- если один journey не сгенерировался, остальные могут быть созданы, но команда завершится с ненулевым кодом

Результат:

- `automation/load/journeys/<journey>.js`
- краткий markdown-отчёт рядом с сценарием

Важные нюансы:

- если в OpenAPI нет `servers[0].url`, в скрипт подставляется `TODO-BASE-URL`
- в генерируемом коде остаются `TODO` для path parameters и зависимостей между шагами
- автоматического связывания ответа одного request с параметрами следующего шага нет

#### Настройка thresholds для k6

Если `--thresholds` не передан, в скрипт добавляется placeholder SLA-подсказка.

Пример `k6-thresholds.json`:

```json
{
  "default": { "p95": 500, "p99": 1000, "error_rate": 0.01 },
  "by_tag": { "payments": { "p95": 300, "p99": 700, "error_rate": 0.005 } }
}
```

## Что хранится в проекте

- `docs/` — входная документация
- `checklist.csv` — основной список Xray-кейсов
- `.state/state.json` — метаданные обработки документов
- `.state/system_overview.md` — обновляемый системный overview
- `automation/api/` — сгенерированные Playwright API-автотесты
- `automation/load/` — сгенерированные k6-journeys и отчёты

## Переменные окружения

- `OPENAI_API_KEY` — ключ OpenAI
- `QA_BASE_PATH` — базовый путь для Xray Test Repository Path
- `QA_TCID_PREFIX` — префикс для TCID, например `QA`

## Примечания

- если документ не менялся, он будет пропущен при следующем запуске
- при наличии некорректных или неполных сгенерированных кейсов они будут пропущены с предупреждением
- проект хранит состояние по содержимому документа и повторно не обрабатывает уже актуальный файл

## Требования

- Python 3.9+
- доступ к OpenAI API
- папка `docs/` с описанием функций и сценариев

## Проверка

```bash
py -m pytest -q
```
