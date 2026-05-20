import httpx

from app.core.config import settings
from app.models import TreasuryResponse


class TreasuryClient:
    def __init__(self) -> None:
        self.url = settings.treasury_api_url

    async def fetch_rates(self) -> TreasuryResponse:
        async with httpx.AsyncClient() as client:
            response = await client.get(self.url)
            response.raise_for_status()
            return TreasuryResponse(**response.json())
