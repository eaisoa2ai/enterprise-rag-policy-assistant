"""Thin wrapper around the OpenAI chat completions API for answer
generation. Deliberately not using a LangChain chat-model wrapper here —
LangGraph's StateGraph nodes are plain callables, so a direct SDK call is
simpler and has one fewer abstraction layer than necessary.
"""
from __future__ import annotations

import json

from policyiq.agent.prompts import GENERATE_SYSTEM_PROMPT, REGENERATE_ADDENDUM
from policyiq.config import settings
from policyiq.models import AnswerDraft, ScoredChunk


def _client():
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. PolicyIQ needs it for answer generation."
        )
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


def _format_context(chunks: list[ScoredChunk]) -> str:
    return "\n\n".join(
        f"[{i + 1}] chunk_id={sc.chunk.chunk_id} doc_id={sc.chunk.doc_id} "
        f"doc_title={sc.chunk.doc_title!r}\n{sc.chunk.text}"
        for i, sc in enumerate(chunks)
    )


def generate_answer(question: str, chunks: list[ScoredChunk], *, strict: bool = False) -> AnswerDraft:
    system_prompt = GENERATE_SYSTEM_PROMPT.format(context=_format_context(chunks))
    if strict:
        system_prompt += REGENERATE_ADDENDUM

    response = _client().chat.completions.create(
        model=settings.openai_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    raw = json.loads(response.choices[0].message.content)
    return AnswerDraft.model_validate(raw)
