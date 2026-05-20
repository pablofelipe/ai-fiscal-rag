from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ai-fiscal-rag"
    treasury_api_url: str = (
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/"
        "accounting/od/rates_of_exchange"
    )
    gemini_api_key: str = ""

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def strip_gemini_api_key(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
