from typing import Literal
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    speech_mode: Literal['disabled', 'gnani', 'fixture'] = 'disabled'
    gnani_api_key: SecretStr | None = None
    database_url: str = 'sqlite:///./bolbus.db'
    cors_origins: list[str] = ['http://localhost:5173']
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()
