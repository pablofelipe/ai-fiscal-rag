from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ai-fiscal-rag"
    treasury_api_url: str = (
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/"
        "accounting/od/rates_of_exchange"
    )
    gemini_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
