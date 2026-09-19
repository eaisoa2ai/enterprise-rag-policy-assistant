"""Embedding provider. Requires a real OpenAI call — unlike outreach-iq's
voice/email providers, there's no meaningful "mock" here: retrieval quality
*is* the thing being demonstrated, and a random vector would just prove
nothing. Kept as a small interface anyway (not a bare function call) so a
different embedding backend is a class swap, not a rewrite — same pattern
as every other provider in this portfolio.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from policyiq.config import settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Returns one embedding vector per input text, same order."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. PolicyIQ needs it for embeddings and "
                "generation — there is no offline mode for retrieval quality."
            )
        from openai import OpenAI

        self._client = OpenAI(api_key=settings.openai_api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=settings.openai_embedding_model, input=texts
        )
        return [item.embedding for item in response.data]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
