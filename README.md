# QA Coverage Agent

CLI-инструмент для автоматизации анализа покрытия тестами и генерации новых тест-кейсов на основе документации системы.

## Описание

QA Coverage Agent — это Python-приложение, которое:

1. **Парсит документацию** — читает описание функций и сценариев из Markdown/текстовых файлов в папке `docs/`
2. **Строит матрицу трассируемости** — сопоставляет сценарии из документов с существующими тест-кейсами из `checklist.csv`
3. **Выявляет пробелы** — идентифицирует недокрытые функции и сценарии
4. **Генерирует тест-кейсы** — создаёт новые ручные тест-кейсы для выявленных пробелов
5. **Экспортирует в Xray** — добавляет кейсы в `checklist.csv` в формате, совместимом с Jira Xray Test Case Importer

**Ключевая цель:** найти пробелы в логическом тестовом покрытии функциональности проекта.

## Структура проекта

```
qa_coverage_agent/
├── checklist.csv              # Единый список всех тест-кейсов (Xray-совместимый формат)
├── docs/                      # Документы о системе/функциях (*.md, *.txt, *.doc, *.csv)
│   ├── auth_feature.md        # Описание функции аутентификации
│   └── payment_feature.md     # Описание функции платежей
├── .state/                    # Служебные файлы (не коммитятся)
│   ├── state.json             # Трекинг обработанных документов
│   └── system_overview.md     # Карта системы (человекочитаемая, редактируемая вручную)
├── src/                       # Исходный код приложения
│   ├── main.py                # Точка входа (CLI)
│   ├── document_parser.py     # Парсинг документов и извлечение сценариев
│   ├── coverage_matrix.py     # Анализ покрытия, выявление пробелов
│   ├── test_designer.py       # Генерация новых тест-кейсов
│   ├── csv_writer.py          # Валидация и запись в checklist.csv
│   ├── system_overview.py     # Работа с картой системы
│   ├── schemas.py             # Pydantic-модели данных
│   ├── llm_client.py          # Обёртка над OpenAI API
│   └── __init__.py
├── tests/                     # Unit-тесты
│   └── test_llm_client.py
├── .env                       # Переменные окружения (не коммитятся)
├── requirements.txt           # Зависимости Python
├── codex.md                   # Техническое задание (архивное)
└── README.md                  # Этот файл
```

## Требования

- **Python** 3.9+
- **OpenAI API Key** (для генерации тест-кейсов через GPT)
- **pip** (менеджер пакетов Python)

## Установка

### 1. Клонируйте репозиторий
```bash
git clone <repository-url>
cd qa_coverage_agent
```

### 2. Создайте виртуальное окружение
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

### 4. Настройте переменные окружения

Создайте файл `.env` в корне проекта:

```env
OPENAI_API_KEY=sk-...                    # Ваш API ключ от OpenAI
QA_BASE_PATH=MyProject                   # Базовый путь в Xray (напр. Ecommerce)
QA_TCID_PREFIX=QA                        # Префикс для ID тест-кейсов (напр. QA-001)
```

Значения по умолчанию:
- `QA_BASE_PATH`: `Project`
- `QA_TCID_PREFIX`: `QA`

## Использование

### Базовое использование — обработка всех документов

```bash
python src/main.py
```

Агент:
1. Сканирует папку `docs/` на предмет новых/изменённых файлов
2. Анализирует содержимое через OpenAI API
3. Сравнивает сценарии с существующими тест-кейсами
4. Генерирует новые кейсы для пробелов
5. Добавляет их в `checklist.csv`

### Обработка конкретного документа

```bash
python src/main.py --doc docs/auth_feature.md
```

Обрабатывает только указанный файл, игнорируя папку `docs/`.

## Рабочий процесс

### 1️⃣ Подготовка документов

Поместите описание функций в папку `docs/`:

```markdown
# Authentication

## Login
Users sign in with email and password.

### Negative cases
- Invalid credentials should not reveal if email exists
- Empty fields must show validation errors

## Password Reset
Users can request a password-reset link via email.
Link expires after 30 minutes.
```

### 2️⃣ Запуск анализа

```bash
python src/main.py
```

Вывод в консоль:
```
[PROCESS] auth_feature.md — обработка...
[COVERAGE] Найдено 5 сценариев, 3 покрыто тестами, 2 пробела
[GAP] Login → Invalid credentials
[GAP] Password Reset → Link expiration
[NEW] Сгенерировано 2 новых тест-кейса (QA-015, QA-016)
[UPDATE] checklist.csv обновлён
```

### 3️⃣ Результаты в checklist.csv

Новые тест-кейсы добавляются в конец файла в формате Xray:

| TCID | Test Summary | Description | Test Type | Test Repository Path | Label | Action | Data | Expected Result |
|------|---|---|---|---|---|---|---|---|
| QA-015 | Login with invalid email | | Manual | MyProject/Auth/Login/Negative | negative | Enter invalid@mail.com | email: invalid@mail.com | System shows generic error (does not reveal email existence) |
| | | | | | | Enter correct password | password: 123456 | |

### 4️⃣ Экспорт в Jira Xray

Используйте [Xray Test Case Importer](https://docs.getxray.app/display/XRAYCLOUD/Import+Test+Cases) для загрузки `checklist.csv` в Jira:

1. Откройте Jira → Xray → Import
2. Выберите `checklist.csv`
3. Выберите проект и папку репозитория
4. Нажмите "Import"

## Формат checklist.csv

Файл использует **Xray-совместимый CSV-формат** (RFC 4180 с экранированием):

| Колонка | Описание | Обязательное |
|---|---|---|
| `TCID` | ID тест-кейса (QA-001, QA-002, ...) | ✅ да |
| `Test Summary` | Название кейса | ✅ да |
| `Description` | Предусловия и контекст | нет |
| `Test Type` | Manual / Automated | ✅ да (Manual) |
| `Test Repository Path` | Путь в репозитории Xray | ✅ да |
| `Label` | Теги: positive, negative, edge-case, smoke, regression, security | нет |
| `Action` | Шаг действия | ✅ да (на каждой строке) |
| `Data` | Тестовые данные для шага | нет |
| `Expected Result` | Ожидаемый результат шага | ✅ да (на каждой строке) |

**Правила:**
- Один тест-кейс = N строк с одинаковым TCID
- Поля `Test Summary`, `Description`, `Test Type`, `Test Repository Path`, `Label` заполняются только на **первой строке** кейса
- На последующих строках (шагам) — только `Action`, `Data`, `Expected Result`
- **Только append** — файл никогда не перезаписывается, только добавляются новые строки

## Система трекинга документов

Агент использует `.state/state.json` для отслеживания обработанных документов и экономии токенов OpenAI:

```json
{
  "processed_documents": {
    "auth_feature.md": {
      "content_hash": "sha256:abc123...",
      "processed_at": "2026-07-19T10:00:00Z",
      "test_case_ids_generated": ["QA-001", "QA-002"]
    }
  }
}
```

**Логика:**
- Перед обработкой вычисляется SHA-256 хеш содержимого
- Если файл не изменился → пропускается (экономия API-запросов)
- Если файл изменился → перепроцессируется целиком
- После генерации кейсов запись обновляется

## Переменные окружения

### OPENAI_API_KEY
Обязательная. API ключ для доступа к OpenAI API.

Получить: https://platform.openai.com/api-keys

### QA_BASE_PATH
Опциональная. Базовый путь для тест-репозитория в Xray.

Пример: `QA_BASE_PATH=Ecommerce` → путь будет `Ecommerce/Auth/Login/Positive`

По умолчанию: `Project`

### QA_TCID_PREFIX
Опциональная. Префикс для ID тест-кейсов.

Пример: `QA_TCID_PREFIX=PROJ` → ID будут `PROJ-001`, `PROJ-002`, ...

По умолчанию: `QA`

## Тестирование

Запуск unit-тестов:

```bash
python -m pytest tests/ -v
```

## Поддерживаемые форматы документов

- `.md` — Markdown
- `.txt` — Текстовые файлы
- `.doc` — MS Word (с ограничениями)
- `.csv` — CSV-файлы

**Исключаются:**
- Файлы, начинающиеся с `_` (служебные)
- `README.md` (этот файл)

## Примеры

### Пример 1: Анализ функции аутентификации

**docs/auth_feature.md:**
```markdown
# Authentication

## Login
Users can log in with email and password.

### Happy path
- Valid email and password accepted

### Edge cases
- Case-sensitive password
- Email validation (RFC 5322)
- Maximum login attempts: 5
```

**Команда:**
```bash
python src/main.py --doc docs/auth_feature.md
```

**Результат:** 2-3 новых тест-кейса добавлены в checklist.csv

### Пример 2: Полный анализ проекта

**docs/ содержит:**
- `auth_feature.md` (не менялся)
- `payment_feature.md` (новый)
- `user_profile.md` (изменился)

**Команда:**
```bash
python src/main.py
```

**Результат:**
- auth_feature.md — **пропущен** (кеш)
- payment_feature.md — **обработан** (новый)
- user_profile.md — **перепроцессирован** (изменился)

## Архитектура

### Основные модули

| Модуль | Назначение |
|---|---|
| `main.py` | CLI-интерфейс, оркестрация процесса |
| `document_parser.py` | Парсинг документов, извлечение текста и структуры |
| `llm_client.py` | Общение с OpenAI API (GPT-4, GPT-3.5-turbo) |
| `schemas.py` | Pydantic-модели для валидации данных |
| `coverage_matrix.py` | Анализ покрытия, сопоставление doc ↔ checklist |
| `test_designer.py` | Генерация новых тест-кейсов через LLM |
| `csv_writer.py` | Валидация и запись в checklist.csv |
| `system_overview.py` | Работа с картой системы (`.state/system_overview.md`) |

### Поток данных

```
docs/*.md
    ↓ [document_parser]
Extracted scenarios
    ↓ [llm_client → GPT]
Parsed features & requirements
    ↓ [coverage_matrix]
Gaps in coverage (недокрытые сценарии)
    ↓ [test_designer]
New test cases (структурированные кейсы)
    ↓ [csv_writer]
checklist.csv (добавление новых строк)
    ↓ [Xray Importer]
Jira Test Cases
```

## Ограничения и известные проблемы

- **Version 01** — базовая функциональность, нет:
  - Интеграции с TMS/Jira API (только CSV-экспорт)
  - CI/CD триггеров
  - UI (только CLI)
- **Точность анализа** зависит от качества документации и модели LLM
- **Токены OpenAI** потребляются при каждой обработке нового/изменённого документа

## Развитие проекта

Планируемые улучшения:
- [ ] Интеграция с Jira REST API для прямой загрузки кейсов
- [ ] Поддержка автоматизированных тест-кейсов
- [ ] Web UI для управления документами и просмотра результатов
- [ ] Webhook-интеграция для автоматической обработки новых PR
- [ ] Поддержка других моделей LLM (Anthropic Claude, Llama и т.д.)
- [ ] Кеширование ответов LLM для экономии токенов

## Лицензия

MIT

## Автор

Разработано для автоматизации QA-процессов.

## Поддержка и вопросы

Для вопросов и отчётов об ошибках используйте Issues в репозитории.

---

**Дата последнего обновления:** 2026-07-20
