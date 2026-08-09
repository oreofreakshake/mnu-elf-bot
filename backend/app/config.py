from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/timetable"
    storage_dir: Path = Path("./data/uploads")
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    max_upload_mb: int = 500
    worker_poll_seconds: float = 1.5
    bot_service_token: str = "local-development-token"
    bot_token: str = ""
    telegram_bot_username: str = ""
    admin_telegram_ids: str = ""
    session_days: int = 7
    secure_cookies: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def administrator_ids(self) -> set[int]:
        return {
            int(value.strip())
            for value in self.admin_telegram_ids.split(",")
            if value.strip()
        }


settings = Settings()
