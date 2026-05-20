# ai-fiscal-rag

Experimental RAG API for fiscal and exchange-rate questions, backed by U.S. Treasury data and Google Gemini.

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

```bash
git clone https://github.com/<your-user>/ai-fiscal-rag.git
cd ai-fiscal-rag
poetry install
cp .env.example .env
# Edit .env and set GEMINI_API_KEY
```

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

## Development

```bash
poetry run ruff check .
poetry run pytest
```

## License

MIT — see [LICENSE](LICENSE).
