"""
Application configuration using Pydantic Settings.
Loads environment variables from .env file.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLMod.ai Configuration
    llmod_api_key: str
    llmod_base_url: str = "https://api.llmod.ai/v1"
    llmod_chat_model: str = "RPRTHPB-gpt-5-mini"
    llmod_embedding_model: str = "RPRTHPB-text-embedding-3-small"

    # Supabase Configuration
    supabase_url: str
    supabase_key: str

    # Pinecone Configuration
    pinecone_api_key: str
    pinecone_index_name: str = "co-teacher-memory"
    pinecone_environment: str = "us-east-1"

    # Application Settings
    debug: bool = False
    budget_limit: float = 13.00
    budget_warning_threshold: float = 10.00
    use_mock_services: bool = False  # Set to True to use mock clients for local testing

    # Team Information
    group_batch_order_number: str = "batch_1_order_9"
    team_name: str = "avi_yehoraz_maya"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
