from pydantic import BaseModel, Field


class FiscalResponse(BaseModel):
    country: str = Field(description="Analyzed country name")
    error_code: str = Field(
        description="Fiscal error code if identified; use empty string if none"
    )
    technical_analysis: str = Field(
        description="Technical analysis based on fiscal context"
    )
    confidence: float = Field(description="Confidence score from 0 to 1")
    sources_used: list[int] = Field(
        description="IDs of context sources used in the analysis"
    )
    next_action: str = Field(description="Suggested next steps for resolution")
