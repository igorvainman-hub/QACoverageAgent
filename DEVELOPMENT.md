# Development Guide

Руководство для локальной разработки проекта QA Coverage Agent.

## Prerequisites

- Python 3.9+
- Git
- pip (обычно идёт с Python)
- Опционально: virtualenv, poetry, или другой менеджер виртуального окружения

## Setup

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/your-org/qa_coverage_agent.git
cd qa_coverage_agent
```

### 2. Создайте виртуальное окружение

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установите зависимости

```bash
pip install -r requirements.txt
pip install pytest pytest-cov black isort pylint mypy
```

### 4. Создайте файл `.env`

```bash
cp .env.example .env
```

Отредактируйте `.env` и добавьте ваш `OPENAI_API_KEY`:

```env
OPENAI_API_KEY=sk-your-key-here
QA_BASE_PATH=TestProject
QA_TCID_PREFIX=QA
```

## Running the Project

### Базовый запуск

```bash
python src/main.py
```

### Обработка конкретного документа

```bash
python src/main.py --doc docs/auth_feature.md
```

### С verbose выводом

```bash
python src/main.py --doc docs/payment_feature.md -v
```

## Testing

### Запуск всех тестов

```bash
pytest tests/ -v
```

### Запуск с покрытием

```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

### Запуск конкретного теста

```bash
pytest tests/test_llm_client.py::test_api_response -v
```

### Watch mode (переязать тесты при изменении файлов)

```bash
pip install pytest-watch
ptw tests/
```

## Code Quality

### Форматирование кода с Black

```bash
# Проверить
black src/ tests/ --check --diff

# Автоисправить
black src/ tests/
```

### Сортировка импортов с isort

```bash
# Проверить
isort src/ tests/ --check-only

# Автоисправить
isort src/ tests/
```

### Linting с Pylint

```bash
pylint src/ --max-line-length=100
```

### Type checking с mypy

```bash
mypy src/ --ignore-missing-imports
```

## Project Structure

```
src/
├── main.py              # Entry point
├── document_parser.py   # Parsing docs
├── coverage_matrix.py   # Coverage analysis
├── test_designer.py     # Test case generation
├── csv_writer.py        # CSV export
├── system_overview.py   # System map management
├── schemas.py           # Data models
├── llm_client.py        # OpenAI API wrapper
└── __init__.py

tests/
└── test_llm_client.py   # Unit tests

docs/
├── auth_feature.md      # Example docs
└── payment_feature.md

.state/                 # Auto-generated
├── state.json
└── system_overview.md
```

## Key Modules

### `main.py`
- CLI интерфейс
- Оркестрация процесса
- Аргументы: `--doc` (конкретный файл), `-v` (verbose)

### `document_parser.py`
- Парсинг Markdown/текста из `docs/`
- Извлечение сценариев и структуры

### `llm_client.py`
- Обёртка над OpenAI API
- Отправка prompts к GPT
- Парсинг ответов

### `coverage_matrix.py`
- Сравнение документов с существующими тест-кейсами
- Выявление пробелов (gaps)

### `test_designer.py`
- Генерация новых тест-кейсов для пробелов
- Структурирование шагов и данных

### `csv_writer.py`
- Валидация тест-кейсов
- Запись в `checklist.csv` (Xray-формат)
- TCID-генерация

### `schemas.py`
- Pydantic-модели для типизации
- `GeneratedTestCase`, `TestStep` и т.д.

## Debugging

### Логирование

Добавьте в код:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

### Интерактивная отладка

```python
# Добавьте в код для остановки
import pdb; pdb.set_trace()
```

Или используйте debugger IDE:
- VSCode: Ctrl+Shift+D (Open Debug View)
- PyCharm: Run → Debug

## Git Workflow

### Создание новой ветки

```bash
git checkout -b feature/new-feature
# или
git checkout -b fix/issue-description
```

### Coммиты

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat: добавлена поддержка XYZ"
git commit -m "fix: исправлена ошибка при парсинге"
git commit -m "docs: обновлена документация"
```

### Push и Pull Request

```bash
git push origin feature/new-feature
```

Затем создайте Pull Request на GitHub.

## Environment Variables

| Переменная | Описание | По умолчанию |
|---|---|---|
| `OPENAI_API_KEY` | API ключ OpenAI | (обязательная) |
| `QA_BASE_PATH` | Базовый путь Xray | `Project` |
| `QA_TCID_PREFIX` | Префикс ID кейсов | `QA` |

## Common Issues

### ImportError при запуске

```
ModuleNotFoundError: No module named 'src'
```

**Решение:** Убедитесь, что вы в корне проекта и виртуальное окружение активировано.

### OpenAI API Error

```
AuthenticationError: Invalid API key
```

**Решение:** Проверьте, что `OPENAI_API_KEY` правильно установлен в `.env`.

### CSV файл заблокирован

```
PermissionError: [Errno 13] Permission denied: 'checklist.csv'
```

**Решение:** Закройте файл в Excel/другом редакторе, затем повторите запуск.

## Performance

### Профилирование

```python
import cProfile
import pstats

cProfile.run('your_function()', 'stats')
p = pstats.Stats('stats')
p.sort_stats('cumulative').print_stats(10)
```

### Оптимизация LLM вызовов

- Используется кеширование в `.state/state.json`
- Документы не перепроцессируются, если хеш контента не изменился

## Contributing

Перед отправкой PR убедитесь:

- [ ] Код отформатирован (`black`)
- [ ] Импорты отсортированы (`isort`)
- [ ] Тесты проходят (`pytest`)
- [ ] Нет ошибок типов (`mypy`)

Подробнее в [CONTRIBUTING.md](CONTRIBUTING.md).

## Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Python Code Style Guide (PEP 8)](https://pep8.org/)

---

Вопросы? Создайте [Issue](https://github.com/your-org/qa_coverage_agent/issues) или [Discussion](https://github.com/your-org/qa_coverage_agent/discussions).
