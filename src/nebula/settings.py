"""Source credentials loaded from the environment or a local .env file."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Credentials for source adapters.

    Environment variables override values in the working directory's
    ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    congress_gov_api_key: SecretStr | None = None


settings = Settings()
