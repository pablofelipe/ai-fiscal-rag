# ai-fiscal-rag

[![ci](https://github.com/pablofelipe/ai-fiscal-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/pablofelipe/ai-fiscal-rag/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Experimental RAG API for fiscal and exchange-rate questions, backed by U.S. Treasury data and Google Gemini.

See [STATUS.md](STATUS.md) for what works today, known limitations, and
what's deliberately not built yet.

## Features

- **Semantic retrieval** — Sentence embeddings + ChromaDB over Treasury exchange-rate records
- **RAG pipeline** — Retrieve → re-rank with LLM → generate structured answers
- **Intent guardrails** — Off-topic questions are rejected before retrieval
- **Session memory** — Short in-memory conversation history per `session_id`
- **Structured output** — JSON responses validated with Pydantic (`FiscalResponse`)
- **Audit logging** — Requests logged to `logs/ai_search_audit.log`

## Requirements

- Python 3.13+
- [Poetry](https://python-poetry.org/)
- A [Google Gemini API key](https://aistudio.google.com/apikey)

On first run, `sentence-transformers` downloads the `all-MiniLM-L6-v2` model (~80MB).

## Setup

Requires **Python 3.13** (recommended: [pyenv-win](https://github.com/pyenv-win/pyenv-win)). The repo ships a `.python-version` file.

```bash
git clone https://github.com/pablofelipe/ai-fiscal-rag.git
cd ai-fiscal-rag
pyenv install 3.13.0   # skip if already installed
poetry env use "$(pyenv which python)"
poetry install
cp .env.example .env
# Edit .env and set GEMINI_API_KEY
```

On Windows PowerShell you can run `.\scripts\setup.ps1` to bind Poetry to pyenv and reinstall dependencies.

### Poetry / venv troubleshooting

| Symptom | Fix |
|---------|-----|
| `virtual environment ... seems to be broken` | A stale `.venv` from another machine or project. Close the editor, delete the `.venv` folder, then run `.\scripts\setup.ps1` or `poetry env use "$(pyenv which python)"` + `poetry install`. |
| `[WinError 5] Acesso negado` on `ruff.exe` | The Ruff extension holds `.venv\Scripts\ruff.exe`. Close Cursor/VS Code, delete `.venv`, rerun setup. |
| Poetry picks Python 3.14 instead of 3.13 | Run `poetry env use` with the pyenv 3.13 interpreter (see setup above). |
| `poetry install` fails installing the root package | This app is non-package mode; ensure `pyproject.toml` contains `[tool.poetry]` with `package-mode = false`. |

## Run

```bash
poetry run uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive API.

## API

### `GET /fiscal_search`

| Parameter     | Required | Description                                      |
|---------------|----------|--------------------------------------------------|
| `question`    | Yes      | Fiscal or exchange-rate question                 |
| `country`     | No       | Country name in English (e.g. `Brazil`); inferred from session history if omitted |
| `session_id`  | No       | Conversation session id (default: `default`)     |

**Example**

```bash
curl "http://127.0.0.1:8000/fiscal_search?question=What%20is%20the%20exchange%20rate%20for%20Brazil?&country=Brazil"
```

**Success response**

```json
{
  "message": "Analysis complete",
  "result": {
    "country": "Brazil",
    "error_code": "",
    "technical_analysis": "...",
    "confidence": 0.85,
    "sources_used": [1],
    "next_action": "..."
  }
}
```

## Pipeline

```mermaid
flowchart LR
    A[Question] --> B[Intent validation]
    B --> C[Country resolution]
    C --> D[ChromaDB retrieval]
    D --> E[LLM re-ranking]
    E --> F[Structured generation]
    F --> G[Session memory]
```

## MCP server

`app/mcp_server.py` exposes the RAG pipeline
(`FiscalRagService.handle_fiscal_search`) as a single MCP tool,
`fiscal_search`, over the **stdio** transport, for a local MCP client (e.g.
Claude Desktop, Claude Code). Same inputs/outputs as `GET /fiscal_search`; no
new retrieval or LLM logic. Consistent with
[ADR-0006](docs/adr/0006-direct-coupling-to-gemini-sdk.md), which documents
this project as running locally, for the maintainer only — an MCP server
over stdio is a local integration point and does not expand that Non-Goal.

Run it directly:

```bash
poetry run python -m app.mcp_server
```

Or point an MCP client at it, e.g. in Claude Desktop's config:

```json
{
  "mcpServers": {
    "ai-fiscal-rag": {
      "command": "poetry",
      "args": ["run", "python", "-m", "app.mcp_server"],
      "cwd": "/absolute/path/to/ai-fiscal-rag"
    }
  }
}
```

## Roadmap

Nothing currently planned.

## Development

```bash
poetry run ruff check .
poetry run pytest
```

## License

MIT — see [LICENSE](LICENSE).
