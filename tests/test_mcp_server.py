from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.fiscal_response import FiscalResponse
from app.mcp_server import fiscal_search


def _ctx_with_service(service: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(service=service)
        )
    )


@pytest.mark.asyncio
async def test_fiscal_search_passes_through_dict_error_response():
    service = SimpleNamespace(
        handle_fiscal_search=AsyncMock(
            return_value={
                "message": "Country required",
                "result": {"error_code": "COUNTRY_REQUIRED"},
            }
        )
    )
    ctx = _ctx_with_service(service)

    result = await fiscal_search(ctx, "What is the rate?", "", "session-1")

    assert result == {
        "message": "Country required",
        "result": {"error_code": "COUNTRY_REQUIRED"},
    }
    service.handle_fiscal_search.assert_awaited_once_with(
        "What is the rate?", "", "session-1"
    )


@pytest.mark.asyncio
async def test_fiscal_search_wraps_successful_response():
    fiscal_response = FiscalResponse(
        country="Brazil",
        error_code="",
        technical_analysis="analysis",
        confidence=0.9,
        sources_used=[1],
        next_action="none",
    )
    service = SimpleNamespace(
        handle_fiscal_search=AsyncMock(return_value=fiscal_response)
    )
    ctx = _ctx_with_service(service)

    result = await fiscal_search(ctx, "What is the rate?", "Brazil", "session-1")

    assert result["message"] == "Analysis complete"
    assert result["result"]["country"] == "Brazil"
    assert result["result"]["confidence"] == 0.9
