from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    congress_gov_api_key: str = "changethis"


settings = Settings()
