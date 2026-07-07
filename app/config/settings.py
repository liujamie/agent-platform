from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Default model
    default_model: str = "deepseek-chat"
    default_model_api_base: str = "https://api.deepseek.com"

    # API Keys (optional per provider)
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    dashscope_api_key: str = ""


settings = Settings()
