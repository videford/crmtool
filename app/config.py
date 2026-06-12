from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    database_url: str = "postgresql+asyncpg://crm:crm@localhost:5432/crm"
    session_secret: str = "change-me-in-prod"
    base_url: str = "http://localhost:8000"
    timezone: str = "Europe/Moscow"

    # Seed admin
    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"
    admin_name: str = "Admin"

    # Self-registration
    allow_registration: bool = True
    default_role: str = "manager"  # role assigned to self-registered users

    # Telegram
    telegram_bot_token: str = ""
    reminder_offsets: str = "1440,60,15"

    # Linear
    linear_api_key: str = ""
    linear_team_id: str = ""
    linear_webhook_secret: str = ""

    @property
    def sqlalchemy_url(self) -> str:
        """Normalize the DB URL to the asyncpg driver.

        Railway / Heroku style URLs come as `postgresql://...` or even
        `postgres://...`; SQLAlchemy's async engine needs `postgresql+asyncpg`.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def reminder_offset_minutes(self) -> list[int]:
        out: list[int] = []
        for part in self.reminder_offsets.split(","):
            part = part.strip()
            if part.isdigit():
                out.append(int(part))
        return sorted(set(out), reverse=True)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token)

    @property
    def linear_enabled(self) -> bool:
        return bool(self.linear_api_key and self.linear_team_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
