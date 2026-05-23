"""Async Ollama client with conversational history support."""

import logging
from typing import AsyncIterator

import ollama  # type: ignore[import]

from . import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a concise Discord assistant. "
    "Respond in plain prose only. No markdown, no bullet points, no numbered lists, "
    "no code blocks, no URLs. Keep responses under 3 sentences for voice delivery."
)

VOICE_SYSTEM_PROMPT = SYSTEM_PROMPT

_client: ollama.AsyncClient | None = None

MAX_HISTORY_TURNS = 10


def trim_history(history: list[dict]) -> list[dict]:
    return history[-(MAX_HISTORY_TURNS * 2):]


def _get_client() -> ollama.AsyncClient:
    global _client

    if _client is None:
        _client = ollama.AsyncClient(host=config.OLLAMA_HOST)

    return _client


async def ask(
    prompt: str,
    history: list[dict] | None = None,
    system: str = SYSTEM_PROMPT,
) -> str:
    client = _get_client()

    history = trim_history(history or [])

    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    response = await client.chat(
        model=config.OLLAMA_MODEL,
        messages=messages,
    )

    return response.message.content.strip()


async def ask_stream(prompt: str, system: str = SYSTEM_PROMPT) -> AsyncIterator[str]:
    client = _get_client()

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    async for chunk in await client.chat(
        model=config.OLLAMA_MODEL,
        messages=messages,
        stream=True,
    ):
        delta = chunk.message.content

        if delta:
            yield delta
