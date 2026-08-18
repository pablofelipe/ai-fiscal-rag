import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

import chromadb
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.fiscal_response import FiscalResponse
from app.gemini_service import GeminiService
from app.integrations import TreasuryClient
from app.memory_service import MemoryService

logger = logging.getLogger(__name__)

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

audit_logger = logging.getLogger("ai_audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False

file_handler = logging.FileHandler(LOG_DIR / "ai_search_audit.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
file_handler.setFormatter(formatter)
if not audit_logger.handlers:
    audit_logger.addHandler(file_handler)

def _log_query_error(exc: Exception) -> None:
    """Log query failures without letting Windows logging issues mask the handler."""
    try:
        audit_logger.error(
            "QUERY ERROR | Type: %s | Message: %s",
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
    except OSError:
        audit_logger.error(
            "QUERY ERROR | Type: %s | Message: %s",
            type(exc).__name__,
            str(exc),
        )


def _internal_error_response(exc: Exception) -> dict[str, Any]:
    return {
        "message": "Query failed",
        "result": {
            "technical_analysis": (
                f"An error occurred while processing the query: {exc}"
            ),
            "error_code": "INTERNAL_ERROR",
            "confidence": 0.0,
        },
    }


COUNTRY_ALIASES: dict[str, str] = {
    "brasil": "Brazil",
    "bolivia": "Bolivia",
    "bolívia": "Bolivia",
    "angola": "Angola",
    "equador": "Ecuador",
    "ecuador": "Ecuador",
    "gabon": "Gabon",
    "gabão": "Gabon",
}


class FiscalRagService:
    def __init__(self) -> None:
        self.client = TreasuryClient()
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.db = chromadb.Client()
        self.collection = self.db.get_or_create_collection(name="countries")
        self.memory_service = MemoryService()
        self._data_ready = False

    def normalize_country(self, country: str) -> str:
        cleaned = country.strip()
        if not cleaned:
            return cleaned
        return COUNTRY_ALIASES.get(cleaned.lower(), cleaned)

    async def ingest_data(self) -> None:
        self._data_ready = False
        raw_data = await self.client.fetch_rates()

        if not raw_data or not raw_data.data:
            logger.warning(
                "Treasury ingest returned no data; semantic search will be empty."
            )
            return

        for item in raw_data.data:
            document = (
                f"In {item.country}, the official currency is {item.currency}. "
                f"The recorded exchange rate is {item.exchange_rate}."
            )
            embedding = await asyncio.to_thread(
                self.model.encode,
                [document],
            )
            embedding_list = embedding.tolist()[0]

            self.collection.upsert(
                documents=[document],
                embeddings=[embedding_list],
                metadatas=[{"country": item.country}],
                ids=[f"rate_{item.country}_{item.record_date}"],
            )

        self._data_ready = True
        logger.info("Treasury ingest complete (%s records).", len(raw_data.data))

    async def search_in_chromadb(
        self,
        query: str,
        country: str | None = None,
        results_count: int = 5,
    ) -> dict:
        normalized_country = self.normalize_country(country) if country else None
        search_text = (
            f"{normalized_country}. {query}" if normalized_country else query
        )
        encoded = await asyncio.to_thread(self.model.encode, [search_text])
        query_embedding = encoded.tolist()

        query_kwargs: dict[str, Any] = {
            "query_embeddings": query_embedding,
            "n_results": results_count,
        }
        if normalized_country:
            query_kwargs["where"] = {"country": normalized_country}

        results = self.collection.query(**query_kwargs)

        if normalized_country:
            results = self.filter_results_by_country(results, normalized_country)

        return results

    def filter_results_by_country(
        self, chroma_results: dict, country: str
    ) -> dict:
        """Keep only documents whose metadata matches the target country."""
        documents = chroma_results.get("documents", [[]])[0]
        metadatas = chroma_results.get("metadatas", [[]])[0]

        filtered_docs: list[str] = []
        filtered_metas: list[dict] = []
        target = country.lower()

        for doc, meta in zip(documents, metadatas, strict=True):
            meta_country = (meta or {}).get("country", "")
            if meta_country.lower() == target:
                filtered_docs.append(doc)
                filtered_metas.append(meta)

        return {"documents": [filtered_docs], "metadatas": [filtered_metas]}

    def filter_results_by_id(
        self, chroma_results: dict, relevant_ids: list[int]
    ) -> dict:
        """Keep only documents selected by LLM re-ranking."""
        if not relevant_ids:
            return {"documents": [[]], "metadatas": [[]]}

        original_docs = chroma_results.get("documents", [[]])[0]
        original_metas = chroma_results.get("metadatas", [[]])[0]

        filtered_docs: list[str] = []
        filtered_metas: list[dict] = []

        for doc_id in relevant_ids:
            list_idx = doc_id - 1
            if 0 <= list_idx < len(original_docs):
                filtered_docs.append(original_docs[list_idx])
                filtered_metas.append(original_metas[list_idx])

        return {"documents": [filtered_docs], "metadatas": [filtered_metas]}

    async def handle_fiscal_search(
        self,
        question: str,
        country: str,
        session_id: str = "default",
    ) -> FiscalResponse | dict[str, Any]:
        try:
            if not getattr(self, "_data_ready", False):
                return {
                    "message": "Data not ready",
                    "result": {
                        "technical_analysis": (
                            "Treasury data is still loading or failed to ingest. "
                            "Wait for startup to finish and try again."
                        ),
                        "error_code": "DATA_NOT_READY",
                        "confidence": 0.0,
                    },
                }

            history = self.memory_service.get_history(session_id)

            if not settings.gemini_api_key:
                return {
                    "message": "Configuration error",
                    "result": {
                        "technical_analysis": (
                            "GEMINI_API_KEY is not set. "
                            "Copy .env.example to .env and add your key."
                        ),
                        "error_code": "MISSING_API_KEY",
                        "confidence": 0.0,
                    },
                }

            gemini = GeminiService(settings.gemini_api_key)

            is_valid = await gemini.validate_intent(question)

            if not is_valid:
                audit_logger.warning("BLOCKED INTENT | Question: %s", question)
                return {
                    "message": "Query out of scope",
                    "result": {
                        "technical_analysis": (
                            "This assistant is limited to fiscal and "
                            "exchange-rate questions. It cannot help with that topic."
                        ),
                        "error_code": "OUT_OF_SCOPE",
                        "confidence": 1.0,
                    },
                }

            if not country or country.lower() == "string":
                audit_logger.info(
                    "Country not provided. Inferring from memory for session %s...",
                    session_id,
                )
                identified_country = await gemini.identify_country_context(
                    question, history
                )

                if identified_country != "None":
                    country = identified_country
                    audit_logger.info("Country inferred from history: %s", country)
                else:
                    return {
                        "message": "Country required",
                        "result": {
                            "error": "Please specify the country.",
                            "error_code": "COUNTRY_REQUIRED",
                        },
                    }

            target_country = self.normalize_country(country)
            chroma_results = await self.search_in_chromadb(
                question, country=target_country
            )
            start_time = datetime.now()

            audit_logger.info(
                "QUERY START | Country: %s | Question: %s",
                target_country,
                question,
            )

            candidate_text = self.prepare_context(chroma_results)
            audit_logger.info("RETRIEVED CONTEXT: %s...", candidate_text[:200])

            relevant_ids = await gemini.rerank_results(
                question, candidate_text, target_country
            )
            audit_logger.info("Relevant IDs: %s", relevant_ids)

            refined_results = self.filter_results_by_id(chroma_results, relevant_ids)
            refined_results = self.filter_results_by_country(
                refined_results, target_country
            )
            audit_logger.info("Refined results: %s", refined_results)

            refined_context = self.prepare_context(refined_results)
            final_result = await gemini.generate_analysis(
                question, refined_context, history, target_country
            )
            if not final_result.country.strip():
                final_result = final_result.model_copy(
                    update={"country": target_country}
                )

            self.memory_service.add_message(session_id, "User", question)
            self.memory_service.add_message(
                session_id, "Assistant", final_result.technical_analysis
            )

            duration = datetime.now() - start_time
            audit_logger.info(
                "QUERY END | Success | Duration: %ss | Confidence: %s | Country: %s",
                duration.total_seconds(),
                final_result.confidence,
                final_result.country,
            )

        except Exception as exc:
            _log_query_error(exc)
            return _internal_error_response(exc)

        return final_result

    def prepare_context(
        self, chroma_results: dict[str, Any], max_tokens: int = 4000
    ) -> str:
        """Format ChromaDB hits into a prompt-ready context string."""
        documents = chroma_results.get("documents", [[]])[0]
        metadatas = chroma_results.get("metadatas", [[]])[0]

        if not documents:
            return "No data found for this query."

        formatted_blocks: list[str] = []
        total_chars = 0

        for index, (doc, meta) in enumerate(
            zip(documents, metadatas, strict=True)
        ):
            block = f"ID: {index + 1}:\nContent: {doc}\n"

            if meta and isinstance(meta, dict):
                details = ", ".join(f"{key}: {value}" for key, value in meta.items())
                block += f"Details: {details}\n"

            block += "-" * 20

            if total_chars + len(block) > (max_tokens * 4):
                logger.warning("Context limit reached; truncating retrieval.")
                break

            formatted_blocks.append(block)
            total_chars += len(block)

        return "\n".join(formatted_blocks)
