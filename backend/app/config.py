from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    ai_provider: str = "openai"
    ai_api_key: SecretStr | None = None
    ai_model: str | None = None
    ai_timeout_seconds: float = Field(default=30.0, gt=0)
    frontend_origins: str = "http://localhost:5173"
    # Archivo SQLite donde se guardan los casos. Se crea solo la primera vez que se usa.
    database_path: Path = PROJECT_ROOT / "data" / "seci_ti.sqlite3"
    aws_enabled: bool = False
    aws_allow_deployments: bool = False
    aws_region: str = Field(default="us-east-1", pattern=r"^[a-z]{2}(?:-[a-z]+)+-\d+$")
    aws_profile: str | None = None
    aws_access_key_id: SecretStr | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_session_token: SecretStr | None = None
    aws_expected_account_id: str | None = Field(default=None, pattern=r"^\d{12}$")
    aws_stack_prefix: str = Field(default="seci-ti", pattern=r"^[A-Za-z][A-Za-z0-9-]{0,39}$")
    aws_instance_type: Literal["t2.micro", "t3.micro"] = "t3.micro"

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
