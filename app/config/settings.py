from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_secret_key: str = Field(min_length=32)
    admin_username: str = "admin"
    admin_password_hash: str = ""
    database_url: str = "sqlite:///./keyport.db"
    base_url: str = "http://localhost:8000"
    environment: Literal["development", "test", "production"] = "development"
    trusted_hosts: str = "localhost,127.0.0.1,testserver"

    @field_validator("base_url")
    @classmethod
    def strip_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def hosts(self) -> list[str]:
        hosts = [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]
        return list(dict.fromkeys([*hosts, "127.0.0.1"]))


@lru_cache
def get_settings() -> Settings:
    return Settings()
