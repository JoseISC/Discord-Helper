"""
Motor de transcripción de voz usando faster-whisper.

Sprint 4:
- lazy singleton asíncrono
- carga no bloqueante
- cleanup seguro de temporales
"""

import asyncio
import io
import logging
import os
import tempfile
from typing import Optional

from faster_whisper import WhisperModel

from . import config

logger = logging.getLogger(__name__)

_model: WhisperModel | None = None
_model_lock = asyncio.Lock()


def _load_model_sync() -> WhisperModel:
    logger.info(
        "Cargando modelo Whisper '%s' en %s con compute_type=%s ...",
        config.WHISPER_MODEL,
        config.WHISPER_DEVICE,
        config.WHISPER_COMPUTE_TYPE,
    )

    return WhisperModel(
        config.WHISPER_MODEL,
        device=config.WHISPER_DEVICE,
        compute_type=config.WHISPER_COMPUTE_TYPE,
    )


async def get_model() -> WhisperModel:
    global _model

    if _model is not None:
        return _model

    async with _model_lock:
        if _model is None:
            _model = await asyncio.to_thread(_load_model_sync)
            logger.info("Modelo Whisper cargado correctamente")

    return _model


async def _transcribe_async(audio_bytes: bytes, language: Optional[str]) -> str:
    model = await get_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments, info = await asyncio.to_thread(
            model.transcribe,
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        text = " ".join(seg.text.strip() for seg in segments).strip()

        logger.debug(
            "Transcripción completada. Idioma=%s Texto=%r",
            info.language,
            text,
        )

        return text

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def transcribe(audio_buffer: io.BytesIO, language: Optional[str] = None) -> str:
    effective_language = language or config.ASR_LANGUAGE
    audio_bytes = audio_buffer.read()

    if not audio_bytes:
        return ""

    return await _transcribe_async(audio_bytes, effective_language)
