# QA Coverage Agent

CLI project for analyzing functional coverage from documentation, identifying gaps, and generating ready-to-use test artifacts for Xray, API tests, and k6 load paths.

## What the project does

The project supports three main scenarios:

1. Manual Xray test case generation from Markdown documents
   - reads files from the `docs/` folder
   - maps scenarios to existing cases in `checklist.csv`
   - identifies coverage gaps
   - creates new test cases and updates `.state/system_overview.md`

2. API test generation with Playwright
   - reads cases from `checklist.csv` tagged with `api`
   - analyzes the OpenAPI specification
   - creates clients by `tags`
   - generates specs under `automation/api`

3. k6 load-test generation from journeys
   - accepts a set of TCIDs in the required execution order
   - maps them to endpoints from OpenAPI
   - creates one or more k6 scripts and markdown reports

## Architecture

Main modules:

- `src/main.py` — CLI entry point
- `src/app/pipeline.py` — document processing pipeline and state persistence
- `src/agents/` — agents for coverage, test design, OpenAPI, and load generation
- `src/config.py` — runtime configuration loading
- `src/llm_client.py` — LLM wrapper
- `src/document_parser.py` — document parsing
- `src/csv_writer.py` — Xray case writing and validation

## Quick start

### 1. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Configure the environment

Create an `.env` file:

```env
OPENAI_API_KEY=sk-...
QA_BASE_PATH=MyProject
QA_TCID_PREFIX=QA
```

### 3. CLI commands

#### Generate manual test cases from documents

```bash
python -m src.main generate-docs
```

Or just one document:

```bash
python -m src.main generate-docs --doc payment_feature.md
```

Dry run:

```bash
python -m src.main generate-docs --dry-run
```

Verbose output:

```bash
python -m src.main generate-docs --verbose
```

#### Generate API tests

To work on real data, `checklist.csv` must contain at least one case tagged with `API` or `Smoke;API`.

Examples:

```bash
python -m src.main generate-tests --openapi docs/openapi.json --output-dir automation/api
python -m src.main generate-tests --openapi docs/openapi.json --dry-run --verbose
```

What this mode does:

- reads the OpenAPI specification
- creates clients by `tags`
- generates Playwright specs
- adds `fixtures/auth.ts` and `coverage-report.md` when needed

Limitations:

- only OpenAPI JSON specifications are supported
- public URLs are allowed only for open HTTP(S) resources
- loopback, private, link-local, reserved, and redirect addresses are blocked
- for internal APIs, it is better to pass a local JSON file

#### Generate k6 load tests

This command creates one or more k6 scripts for linear API journeys.

```bash
python -m src.main generate-load-tests --openapi docs/openapi.json --journey QA-API-001,QA-API-003 --base-url http://testURL --vus 150 --duration 4m --output-dir automation/load
python -m src.main generate-load-tests --openapi docs/openapi.json --journey QA-101,QA-104,QA-110
python -m src.main generate-load-tests --openapi docs/openapi.json --journey QA-101,QA-104 --thresholds k6-thresholds.json --vus 50 --duration 2m --output-dir automation/load
python -m src.main generate-load-tests --openapi docs/openapi.json --journey QA-101,QA-104 --journey QA-201,QA-220
```

Rules:

- TCIDs must already exist in `checklist.csv`
- the order of TCIDs must be the exact execution order
- each `--journey` creates an independent scenario
- if one journey is not generated, the others may still be created, but the command will exit with a non-zero status

Result:

- `automation/load/journeys/<journey>.js`
- a concise markdown report next to the scenario

Important notes:

- if `servers[0].url` is missing in the OpenAPI document, `TODO-BASE-URL` is inserted into the script
- generated code still contains `TODO` markers for path parameters and dependencies between steps
- there is no automatic binding of one request response to the parameters of the next step

#### Configure k6 thresholds

If `--thresholds` is omitted, a placeholder SLA hint is added to the script.

Example `k6-thresholds.json`:

```json
{
  "default": { "p95": 500, "p99": 1000, "error_rate": 0.01 },
  "by_tag": { "payments": { "p95": 300, "p99": 700, "error_rate": 0.005 } }
}
```

## What is stored in the project

- `docs/` — input documentation
- `checklist.csv` — the main Xray test case list
- `.state/state.json` — document processing metadata
- `.state/system_overview.md` — updated system overview
- `automation/api/` — generated Playwright API tests
- `automation/load/` — generated k6 journeys and reports

## Environment variables

- `OPENAI_API_KEY` — OpenAI API key
- `QA_BASE_PATH` — base path for Xray Test Repository Path
- `QA_TCID_PREFIX` — TCID prefix, for example `QA`

## Notes

- if a document has not changed, it will be skipped on the next run
- if invalid or incomplete generated cases are present, they will be skipped with a warning
- the project stores state by document content and does not reprocess an already up-to-date file

## Requirements

- Python 3.9+
- access to the OpenAI API
- the `docs/` folder with functional and scenario descriptions

## Verification

```bash
py -m pytest -q
```
