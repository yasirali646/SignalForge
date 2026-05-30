from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.services.runtime_settings import load_overrides

# Always load .env from project root (not shell cwd)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    brightdata_api_token: str = ""
    brightdata_mcp_url: str = Field(
        default="",
        validation_alias=AliasChoices("BRIGHTDATA_MCP", "BRIGHTDATA_MCP_URL"),
    )
    brightdata_serp_zone: str = "serp_api1"
    brightdata_scraper_zone: str = "web_scraper1"
    brightdata_unlocker_zone: str = "web_unlocker1"
    brightdata_request_url: str = "https://api.brightdata.com/request"

    # Optional legacy — agent no longer uses OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-oss-120b"

    brightdata_mcp_groups: str = "advanced_scraping"
    agent_mode: str = "brightdata_mcp"  # brightdata_mcp | openrouter (legacy)

    database_url: str = "sqlite:///./data/pulse.db"
    collector_mode: str = "brightdata"  # brightdata | local
    demo_use_fixtures: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    scheduler_enabled: bool = True
    scheduler_interval_hours: float = 6.0

    auth_enabled: bool = True
    auth_username: str = "admin"
    auth_password: str = "signalforge"
    auth_demo_username: str = "demo"
    auth_demo_password: str = "demo"
    auth_secret_key: str = "change-me-in-production-use-long-random-string"
    auth_token_expire_hours: float = 24.0
    demo_agent_request_limit: int = 5

    def resolved_mcp_url(self) -> str:
        if self.brightdata_mcp_url.strip():
            url = self.brightdata_mcp_url.strip()
            if "groups=" not in url and self.brightdata_mcp_groups.strip():
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}groups={self.brightdata_mcp_groups.strip()}"
            return url
        token = self.brightdata_api_token.strip()
        if not token:
            return ""
        groups = self.brightdata_mcp_groups.strip() or "advanced_scraping"
        return f"https://mcp.brightdata.com/sse?token={token}&groups={groups}"

    def agent_configured(self) -> bool:
        return bool(self.resolved_mcp_url())

    def agent_model_label(self) -> str:
        return "Bright Data MCP Agent (LangGraph)"


@lru_cache
def get_settings() -> Settings:
    base = Settings()
    overrides = load_overrides()
    if not overrides:
        return base
    return base.model_copy(update=overrides)


# Presets shown in the Settings UI (hours)
SCHEDULER_INTERVAL_PRESETS: list[tuple[str, float]] = [
    ("Every 15 minutes", 0.25),
    ("Every 30 minutes", 0.5),
    ("Every 1 hour", 1.0),
    ("Every 3 hours", 3.0),
    ("Every 6 hours", 6.0),
    ("Every 12 hours", 12.0),
    ("Every 24 hours", 24.0),
]

MIN_SCHEDULER_INTERVAL_HOURS = 0.25
MAX_SCHEDULER_INTERVAL_HOURS = 168.0


def reload_settings() -> Settings:
    """Clear cached settings after .env changes (call on API startup)."""
    get_settings.cache_clear()
    return get_settings()
