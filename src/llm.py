"""
Cliente asíncrono para el LLM local via Ollama.

Usa ollama.AsyncClient para no bloquear el event loop de Discord.
Incluye timeout configurable y manejo de errores de conectividad.
"""

import logging
import re
from typing import AsyncIterator

import ollama

from . import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Eres un asistente inteligente y servicial integrado en un servidor de Discord. "
    "Responde de forma concisa y clara. Si el usuario habla en español, responde en español. "
    "Si habla en inglés, responde en inglés."
)

# Prompt de sistema optimizado para TTS: sin Markdown, sin emojis, texto plano.
VOICE_SYSTEM_PROMPT = (
    "Eres un asistente de voz. Responde de forma breve y exclusivamente en texto plano. "
    "No uses asteriscos, guiones, ni formato Markdown. No uses listas ni emojis. "
    "Solo palabras y signos de puntuación básicos como punto, coma y signos de interrogación. "
    "Máximo 3 oraciones."
)

_MARKDOWN_RE = re.compile(
    r"\[([^\]]+)\]\([^)]+\)"   # links Markdown [texto](url) → texto
    r"|[*_`#~]+"               # negrita, cursiva, código, encabezados, tachado
    r"|\n{2,}"                 # saltos de línea múltiples → espacio
)


def strip_markdown(text: str) -> str:
    """
    Elimina marcado Markdown residual del texto antes de enviarlo al TTS.
    Actúa como defensa en profundidad por si el LLM ignora el system prompt.
    """
    cleaned = _MARKDOWN_RE.sub(
        lambda m: m.group(1) if m.group(1) else " ", text
    )
    # Colapsar espacios múltiples que puedan quedar tras la sustitución
    cleaned = re.sub(r" {2,}", " ", cleaned).strip()
    return cleaned

_client: ollama.AsyncClient | None = None


def _get_client() -> ollama.AsyncClient:
    """Devuelve una instancia compartida del cliente Ollama."""
    global _client
    if _client is None:
        _client = ollama.AsyncClient(host=config.OLLAMA_HOST)
    return _client


async def ask(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    """
    Envía `prompt` al LLM y devuelve la respuesta completa como cadena.

    Args:
        prompt: Texto del usuario (transcripción o pregunta directa).
        system: Prompt de sistema que define el comportamiento del LLM.

    Returns:
        Respuesta generada por el modelo.

    Raises:
        ollama.ResponseError: Si el modelo no existe o Ollama devuelve error.
        ConnectionError: Si no se puede conectar al servidor Ollama.
    """
    client = _get_client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    logger.debug("Enviando a Ollama (modelo=%s): %r", config.OLLAMA_MODEL, prompt[:120])

    try:
        response = await client.chat(
            model=config.OLLAMA_MODEL,
            messages=messages,
        )
        answer: str = response.message.content.strip()
        logger.debug("Respuesta de Ollama: %r", answer[:120])
        return answer
    except ollama.ResponseError as exc:
        logger.error("Ollama ResponseError: %s", exc)
        raise
    except Exception as exc:
        logger.error("No se pudo conectar a Ollama en %s: %s", config.OLLAMA_HOST, exc)
        raise ConnectionError(
            f"No se pudo contactar a Ollama en {config.OLLAMA_HOST}. "
            "Asegúrate de que el servidor esté corriendo."
        ) from exc


async def ask_stream(prompt: str, system: str = SYSTEM_PROMPT) -> AsyncIterator[str]:
    """
    Versión streaming de `ask`. Genera fragmentos de texto conforme
    el modelo los produce. Útil para respuestas largas.
    """
    client = _get_client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    try:
        async for chunk in await client.chat(
            model=config.OLLAMA_MODEL,
            messages=messages,
            stream=True,
        ):
            delta = chunk.message.content
            if delta:
                yield delta
    except Exception as exc:
        logger.error("Error en streaming con Ollama: %s", exc)
        raise
