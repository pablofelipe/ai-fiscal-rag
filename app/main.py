from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.fiscal_rag_service import FiscalRagService


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting application and ingesting Treasury data for semantic search...")
    service = FiscalRagService()
    await service.ingest_data()
    app.state.fiscal_rag_service = service
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "message": "Query failed",
            "result": {
                "technical_analysis": f"Unexpected server error: {exc}",
                "error_code": "INTERNAL_ERROR",
                "confidence": 0.0,
            },
        },
    )


@app.get("/fiscal_search")
async def fiscal_search(
    request: Request,
    question: str,
    country: str = "",
    session_id: str = "default",
):
    service: FiscalRagService = request.app.state.fiscal_rag_service
    result = await service.handle_fiscal_search(question, country, session_id)

    if isinstance(result, dict):
        return result

    return {
        "message": "Analysis complete",
        "result": result.model_dump(),
    }
