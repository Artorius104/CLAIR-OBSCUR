import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CLAIR OBSCUR API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database — built from individual env vars (matching docker-compose)
    POSTGRES_USER: str = "divinandretomadam"
    POSTGRES_PASSWORD: str = "oDAnmvidrTnmeiAa"
    POSTGRES_DB: str = "spark_streaming_db"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432

    # Agents service URL
    AGENTS_URL: str = "http://agents:8001"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
