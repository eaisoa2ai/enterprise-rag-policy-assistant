from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Deliberately cwd-based, not derived from __file__ — see outreach-iq's
# config.py for why: this resolves incorrectly once the package is installed
# non-editably (e.g. in a Docker image). Every entry point here runs from the
# project root.
PROJECT_ROOT = Path.cwd()


class Thresholds(BaseModel):
    confidence_floor: float = 0.6
    min_relevance_score: float = 0.35
    max_retrieval_attempts: int = 2
    top_k: int = 4
    groundedness_overlap_floor: float = 0.35
    chunk_size_chars: int = 800
    chunk_overlap_chars: int = 120


def _load_thresholds() -> Thresholds:
    path = PROJECT_ROOT / "config" / "settings.yaml"
    if not path.exists():
        return Thresholds()
    raw = yaml.safe_load(path.read_text()) or {}
    return Thresholds(**raw.get("thresholds", {}))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    vectorstore_path: str = "./vectorstore/index.json"
    documents_dir: str = "./data/documents"

    thresholds: Thresholds = Field(default_factory=_load_thresholds)


settings = Settings()
