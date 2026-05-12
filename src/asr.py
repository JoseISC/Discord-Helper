"""
Motor de transcripción de voz usando faster-whisper.

La carga del modelo y la inferencia son operaciones bloqueantes (GPU/CPU),
por lo que se ejecutan en un hilo separado via asyncio.to_thread para no
bloquear el event loop de Discord.
"""

import asyncio
import io
import logging
import tempfile
import os
from functools import lru_cache
from typing import Optional

from faster_whisper import WhisperModel

from . import config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model() -> WhisperModel:
    """
    Carga el modelo Whisper una sola vez y lo reutiliza en llamadas posteriores.
    Se usa lru_cache para garantizar una única instancia (patrón singleton ligero).
    """
    logger.info(
        "Cargando modelo Whisper '%s' en %s con compute_type=%s ...",
        config.WHISPER_MODEL,
        config.WHISPER_DEVICE,
        config.WHISPER_COMPUTE_TYPE,
    )
    try:
        model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Modelo Whisper cargado correctamente.")
        return model
    except Exception as exc:
        logger.error("Error al cargar el modelo Whisper: %s", exc)
        raise


def _transcribe_sync(audio_bytes: bytes, language: Optional[str]) -> str:
    """
    Transcribe audio de forma síncrona (bloquea el hilo actual).
    Escribe los bytes en un archivo temporal WAV, transcribe y lo elimina.
    """
    model = _get_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments, info = model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # ignora silencios automáticamente
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.debug(
            "Transcripción completada. Idioma detectado: %s (prob=%.2f). Texto: %r",
            info.language,
            info.language_probability,
            text,
        )
        return text
    finally:
        os.unlink(tmp_path)


async def transcribe(audio_buffer: io.BytesIO, language: Optional[str] = None) -> str:
    """
    Transcribe el audio contenido en `audio_buffer` de forma asíncrona.

    Args:
        audio_buffer: Buffer WAV en memoria (BytesIO).
        language: Código de idioma ISO-639-1 ("es", "en") o None para auto-detección.

    Returns:
        Texto transcrito. Cadena vacía si no se detectó voz.
    """
    effective_language = language or config.ASR_LANGUAGE
    audio_bytes = audio_buffer.read()

    if not audio_bytes:
        logger.warning("transcribe() recibió un buffer vacío.")
        return ""

    try:
        text = await asyncio.to_thread(_transcribe_sync, audio_bytes, effective_language)
        return text
    except Exception as exc:
        logger.error("Error durante la transcripción: %s", exc)
        raise
