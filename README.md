# QA Coverage Agent

QA Coverage Agent analyzes product documentation, finds missing test coverage, and generates test artifacts.

It supports:

- manual Xray test cases from documents;
- Playwright API tests from an OpenAPI specification;
- k6 load-test journeys from existing test case IDs;
- a Streamlit web interface for document processing and test inventory.

## Setup

Requirements: Python 3.9+ and an OpenAI API key.

```bash
python -m pip install -r requirements.txt
```

Create `.env` in the project root:

```env
OPENAI_API_KEY=sk-...
QA_BASE_PATH=MyProject
QA_TCID_PREFIX=QA
```

Add source documents to `docs/` and the existing Xray cases to `checklist.csv`.

## Run

### Web interface

```bash
streamlit run src/web.py
```

The web interface shows document status and the test inventory, accepts document uploads, and starts test generation.

### Command line

Generate manual Xray cases from all documents:

```bash
python -m src.main generate-docs
```

Process one document or preview changes:

```bash
python -m src.main generate-docs --doc payment_feature.md
python -m src.main generate-docs --dry-run
```

Generate Playwright API tests. The checklist must contain cases labeled `api`:

```bash
python -m src.main generate-tests --openapi docs/openapi.json
```

Generate a k6 journey. TCIDs must exist in `checklist.csv` and remain in execution order:

```bash
python -m src.main generate-load-tests \
  --openapi docs/openapi.json \
  --journey QA-101,QA-104 \
  --base-url http://localhost:8080
```

Useful load-test options: `--vus`, `--duration`, `--thresholds`, `--output-dir`, and `--dry-run`.

## Project files

- `docs/` — source documents;
- `checklist.csv` — existing Xray test cases;
- `.state/` — processing state and system overview;
- `automation/api/` — generated Playwright tests;
- `automation/load/` — generated k6 scripts and reports.

## Verify

```bash
py -m pytest -q
```
