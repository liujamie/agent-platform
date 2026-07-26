from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    default_model: str = "deepseek-chat"
    default_model_api_base: str = "https://api.deepseek.com"
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    dashscope_api_key: str = ""

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "root"
    mysql_database: str = "agent_platform"

    # Model clients (JSON array, env-based — legacy)
    model_clients: list[dict[str, Any]] = []
    # Encryption key for model API keys stored in DB
    model_config_key: str = ""

    # Embedding (SiliconFlow)
    siliconflow_api_key: str = ""
    embedding_model: str = "BAAI/bge-large-zh-v1.5"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    @property
    def database_url(self) -> str:
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"


@lru_cache
def get_settings() -> Settings:
    return Settings()
