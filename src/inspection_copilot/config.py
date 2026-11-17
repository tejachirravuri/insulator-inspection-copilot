"""Application settings.

All configuration comes from environment variables (or a local .env file), following the
12-factor approach: the same Docker image runs locally, in CI and in Azure, and only the
environment differs. pydantic-settings validates types at startup, so a typo in a variable
fails fast instead of at the first request.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # postgresql+asyncpg:// selects SQLAlchemy's async driver.
    database_url: str = "postgresql+asyncpg://copilot:copilot@localhost:5432/copilot"

    # Must match the output size of the embedding model (multilingual-e5-small -> 384).
    # Changing it requires a new migration because the vector column has a fixed size.
    embedding_dim: int = 384
    embedding_model: str = "intfloat/multilingual-e5-small"

    # Chunking (see chunking.py). Recorded with every evaluation result.
    chunk_max_words: int = 180
    chunk_overlap_words: int = 40

    log_level: str = "INFO"

    # Claude API. SecretStr keeps the key out of logs, reprs and error messages.
    # The key lives only in .env (git-ignored) or in the cloud's secret store.
    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-opus-5-5"
    agent_effort: str = "medium"  # low | medium | high: thinking depth and token spend
    agent_max_steps: int = 8  # hard cap on tool-calling rounds per question

    # YOLO weights (not in Git) and uploaded images.
    preload_models: bool = True  # load the embedding model at server start
    models_dir: str = "models"
    uploads_dir: str = "data/uploads"


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is parsed once per process."""
    return Settings()
