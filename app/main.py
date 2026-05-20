from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.fiscal_rag_service import FiscalRagService

fiscal_rag_service = FiscalRagService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting application and ingesting Treasury data for semantic search...")
    await fiscal_rag_service.ingest_data()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/fiscal_search")
async def fiscal_search(
    question: str,
    country: str = "",
    session_id: str = "default",
):
    result = await fiscal_rag_service.handle_fiscal_search(
        question, country, session_id
    )

    if isinstance(result, dict):
        return result

    return {
        "message": "Analysis complete",
        "result": result.model_dump(),
    }
