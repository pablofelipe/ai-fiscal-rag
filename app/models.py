from pydantic import BaseModel, Field


class ExchangeRate(BaseModel):
    country: str = Field(alias="country")
    currency: str = Field(alias="currency")
    exchange_rate: float = Field(alias="exchange_rate")
    record_date: str = Field(alias="record_date")


class TreasuryResponse(BaseModel):
    data: list[ExchangeRate]
