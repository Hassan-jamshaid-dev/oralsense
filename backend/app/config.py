from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Optional so the API can start and report "not configured" instead of crashing.
    database_url: str | None = None
    environment: str = "development"
    session_ttl_hours: int = 12
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # None = enabled in development, disabled in production. Explicit true/false overrides.
    allow_registration: bool | None = None
    # Host header allow-list. testserver is for pytest's TestClient. Override in production.
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    # Off by default: X-Forwarded-* is attacker-controlled unless a trusted proxy is in front.
    trust_forwarding: bool = False
    trusted_proxy_ips: str = "127.0.0.1"

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def session_cookie_secure(self) -> bool:
        # Never ship a session cookie over HTTP once ENVIRONMENT=production.
        return True if self.is_production else self.cookie_secure

    @property
    def registration_allowed(self) -> bool:
        if self.allow_registration is not None:
            return self.allow_registration
        return not self.is_production

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def trusted_proxy_ip_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_proxy_ips.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
