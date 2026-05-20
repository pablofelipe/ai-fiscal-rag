from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.fiscal_rag_service import FiscalRagService


@pytest.fixture
def service() -> FiscalRagService:
    with patch.object(FiscalRagService, "__init__", lambda self: None):
        svc = FiscalRagService()
    svc.memory_service = MagicMock()
    svc.memory_service.get_history.return_value = "No previous conversation."
    svc.memory_service.add_message = MagicMock()
    return svc


@pytest.mark.asyncio
async def test_handle_fiscal_search_rejects_invalid_intent(service: FiscalRagService):
    with (
        patch("app.fiscal_rag_service.settings") as mock_settings,
        patch("app.fiscal_rag_service.GeminiService") as mock_gemini_cls,
    ):
        mock_settings.gemini_api_key = "test-key"
        mock_gemini = mock_gemini_cls.return_value
        mock_gemini.validate_intent = AsyncMock(return_value=False)

        result = await service.handle_fiscal_search(
            "Tell me a joke about cats", "Brazil"
        )

    assert result["message"] == "Query out of scope"
    assert result["result"]["error_code"] == "OUT_OF_SCOPE"


@pytest.mark.asyncio
async def test_handle_fiscal_search_requires_country_when_not_inferred(
    service: FiscalRagService,
):
    with (
        patch("app.fiscal_rag_service.settings") as mock_settings,
        patch("app.fiscal_rag_service.GeminiService") as mock_gemini_cls,
    ):
        mock_settings.gemini_api_key = "test-key"
        mock_gemini = mock_gemini_cls.return_value
        mock_gemini.validate_intent = AsyncMock(return_value=True)
        mock_gemini.identify_country_context = AsyncMock(return_value="None")

        result = await service.handle_fiscal_search(
            "What is the current exchange rate?", ""
        )

    assert result["message"] == "Country required"
    assert result["result"]["error_code"] == "COUNTRY_REQUIRED"


@pytest.mark.asyncio
async def test_filter_results_by_id_keeps_selected_documents(
    service: FiscalRagService,
):
    chroma_results = {
        "documents": [["doc-a", "doc-b", "doc-c"]],
        "metadatas": [[{"country": "A"}, {"country": "B"}, {"country": "C"}]],
    }

    filtered = service.filter_results_by_id(chroma_results, [3, 1])

    assert filtered["documents"] == [["doc-c", "doc-a"]]
    assert filtered["metadatas"] == [[{"country": "C"}, {"country": "A"}]]


@pytest.mark.asyncio
async def test_prepare_context_returns_placeholder_when_empty(
    service: FiscalRagService,
):
    assert service.prepare_context({"documents": [[]], "metadatas": [[]]}) == (
        "No data found for this query."
    )


def test_normalize_country_maps_portuguese_aliases(service: FiscalRagService):
    assert service.normalize_country("Brasil") == "Brazil"
    assert service.normalize_country("Brazil") == "Brazil"


def test_filter_results_by_country_keeps_only_target(service: FiscalRagService):
    chroma_results = {
        "documents": [
            [
                "In Brazil, the official currency is Real.",
                "In Bolivia, the official currency is Boliviano.",
            ]
        ],
        "metadatas": [[{"country": "Brazil"}, {"country": "Bolivia"}]],
    }

    filtered = service.filter_results_by_country(chroma_results, "Brazil")

    assert filtered["documents"] == [["In Brazil, the official currency is Real."]]
    assert filtered["metadatas"] == [[{"country": "Brazil"}]]
