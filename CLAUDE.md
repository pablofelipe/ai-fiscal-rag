# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG API for fiscal and exchange-rate questions. Ingests U.S. Treasury exchange-rate data into ChromaDB on startup, then answers user questions using Gemini LLM with semantic retrieval.

## Commands

```powershell
# Setup (Windows, first time)
poetry env use "$(pyenv which python)"
poetry install
cp .env.example .env   # then add GEMINI_API_KEY

# Run
poetry run uvicorn app.main:app --reload

# Test
poetry run pytest

# Run a single test
poetry run pytest tests/test_fiscal_rag_service.py::test_name -v

# Lint / format
poetry run ruff check .
poetry run ruff format .
```

If the Poetry venv is broken (common on Windows after dependency changes), run `.\scripts\setup.ps1` — it kills stale Ruff processes and rebuilds `.venv`.

First startup downloads the `all-MiniLM-L6-v2` embedding model (~80MB) and ingests Treasury data into ChromaDB; subsequent startups skip ingestion if the collection is already populated.

## Architecture

**Request pipeline** (all in `app/fiscal_rag_service.py` orchestrating other modules):

1. **Intent gate** — `GeminiService.validate_intent()` rejects off-topic questions immediately
2. **Country resolution** — Use explicit `country` param or infer from session history via `GeminiService.identify_country()`
3. **Semantic retrieval** — Embed `"{question} {country}"` → ChromaDB `countries` collection → top-N docs
4. **LLM re-ranking** — `GeminiService.rerank_results()` filters and orders retrieved docs by relevance
5. **Structured generation** — `GeminiService.analyze_fiscal_data()` produces a `FiscalResponse` (Pydantic-enforced Gemini schema)
6. **Session memory** — `MemoryService` stores last 5 Q&A turns per `session_id` for follow-up context

**Module responsibilities:**

| File | Role |
|------|------|
| `app/main.py` | FastAPI app, lifespan (data ingestion on startup), `GET /fiscal_search` endpoint |
| `app/fiscal_rag_service.py` | Pipeline orchestration, ChromaDB init/query, country normalization |
| `app/gemini_service.py` | All Gemini calls: intent validation, country ID, re-ranking, structured analysis |
| `app/memory_service.py` | In-memory rolling conversation history (5-message window, keyed by `session_id`) |
| `app/integrations.py` | `TreasuryClient` — async HTTP to U.S. Treasury XML/JSON API |
| `app/fiscal_response.py` | `FiscalResponse` Pydantic model (returned by every successful query) |
| `app/core/config.py` | Pydantic settings loaded from `.env` |

**ChromaDB collection `countries`:** Each document is `"In {country}, the official currency is {currency}. The recorded exchange rate is {exchange_rate}."` with metadata `{"country": str}` and ID `rate_{country}_{record_date}`.

**`FiscalResponse` fields:** `country`, `error_code` (empty on success; `OUT_OF_SCOPE | COUNTRY_REQUIRED | MISSING_API_KEY | DATA_NOT_READY | INTERNAL_ERROR`), `technical_analysis`, `confidence` (0–1), `sources_used` (list of context IDs), `next_action`.

## Key Configuration

| File | Purpose |
|------|---------|
| `.env` | `GEMINI_API_KEY` (required), `TREASURY_API_URL`, `APP_NAME` |
| `.python-version` | pyenv lock at 3.13.0 |
| `pyproject.toml` | Poetry manifest; `package-mode = false` (non-package app) |
| `logs/ai_search_audit.log` | Audit trail — query start/end, retrieved context, confidence, errors |

## Country Handling

`FiscalRagService.normalize_country()` maps Portuguese aliases to Treasury country names (e.g. `"brasil"→"Brazil"`, `"bolívia"→"Bolivia"`). All country inputs pass through this before retrieval.

## n8n Integration (Optional)

`n8n/workflow-n8n-triagem-fiscal.json` is an importable n8n workflow that polls Gmail for `Consulta Fiscal - {Country}` emails, calls `/fiscal_search`, and auto-replies when `confidence >= 0.7` or routes to human review otherwise. Requires ngrok tunnel + Gmail OAuth2 credentials. See `n8n/README.md`.
