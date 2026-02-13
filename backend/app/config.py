from functools import lru_cache
from os import getenv

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="openai/gpt-4o-mini", alias="OPENROUTER_MODEL")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    @property
    def cors_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        OPENROUTER_API_KEY=getenv("OPENROUTER_API_KEY", ""),
        OPENROUTER_MODEL=getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        SUPABASE_URL=getenv("SUPABASE_URL", ""),
        SUPABASE_ANON_KEY=getenv("SUPABASE_ANON_KEY", ""),
        CORS_ORIGINS=getenv("CORS_ORIGINS", "http://localhost:5173"),
    )
