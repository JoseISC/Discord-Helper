"""
Motor de síntesis de voz (TTS) usando facebook/mms-tts-spa via Hugging Face Transformers.

El modelo VITS genera audio a 16 kHz mono. La inferencia es bloqueante (GPU/CPU),
por lo que se ejecuta en un hilo separado via asyncio.to_thread para no bloquear
el event loop de Discord.
"""

import asyncio
import logging
import os
import tempfile
import wave
from functools import lru_cache

import numpy as np
import torch
from transformers import AutoTokenizer, VitsModel

from . import config

logger = logging.getLogger(__name__)


# Device efectivo en runtime; puede degradarse a "cpu" si la GPU falla en inferencia.
_active_device: str = config.TTS_DEVICE


@lru_cache(maxsize=1)
def _load_model() -> tuple["VitsModel", "AutoTokenizer"]:
    """
    Carga el modelo TTS y el tokenizador una sola vez (singleton).
    El primer uso descarga el modelo de Hugging Face Hub si no está en caché.
    """
    logger.info(
        "Cargando modelo TTS '%s' en device=%s ...",
        config.TTS_MODEL,
        _active_device,
    )
    try:
        model = VitsModel.from_pretrained(config.TTS_MODEL)
        model = model.to(_active_device)
        model.eval()
        tokenizer = AutoTokenizer.from_pretrained(config.TTS_MODEL)
        logger.info("Modelo TTS cargado correctamente.")
        return model, tokenizer
    except Exception as exc:
        logger.error("Error al cargar el modelo TTS '%s': %s", config.TTS_MODEL, exc)
        raise


def _run_inference(text: str) -> tuple[np.ndarray, int]:
    """Ejecuta la inferencia del modelo TTS y devuelve (waveform_np, sample_rate)."""
    model, tokenizer = _load_model()

    inputs = tokenizer(text, return_tensors="pt")
    inputs = {k: v.to(_active_device) for k, v in inputs.items()}

    with torch.no_grad():
        output = model(**inputs)

    waveform: np.ndarray = output.waveform.squeeze().cpu().numpy()
    return waveform, model.config.sampling_rate


def _synthesize_sync(text: str) -> str:
    """
    Sintetiza `text` de forma síncrona (bloquea el hilo actual).

    Retorna la ruta absoluta a un archivo WAV temporal (16 kHz, mono, 16-bit PCM).
    El llamador es responsable de eliminar el archivo tras usarlo.

    Si la inferencia falla en GPU (p.ej. por problemas de NVRTC/CUDA), reintenta
    automáticamente en CPU y mantiene el modelo en CPU para llamadas posteriores.
    """
    global _active_device

    try:
        waveform, sample_rate = _run_inference(text)
    except Exception as exc:
        if _active_device != "cpu":
            logger.warning(
                "Inferencia TTS en %s falló (%s). Reintentando en CPU y dejando el "
                "modelo fijado a CPU para las siguientes llamadas.",
                _active_device,
                exc,
            )
            _active_device = "cpu"
            _load_model.cache_clear()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            waveform, sample_rate = _run_inference(text)
        else:
            raise

    # Convertir float32 → int16 (MMS-TTS sample_rate suele ser 16000 Hz)
    pcm16 = (waveform * 32767.0).clip(-32768, 32767).astype(np.int16)

    # Escribir WAV en archivo temporal
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1)       # mono
        wf.setsampwidth(2)       # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())

    logger.debug(
        "TTS: '%s...' → %s (%d muestras, %d Hz)",
        text[:60],
        tmp_path,
        len(pcm16),
        sample_rate,
    )
    return tmp_path


async def synthesize(text: str) -> str:
    """
    Sintetiza `text` de forma asíncrona.

    Args:
        text: Texto plano a sintetizar (sin Markdown ni caracteres especiales).

    Returns:
        Ruta absoluta al archivo WAV temporal generado.
        El llamador debe eliminar el archivo tras reproducirlo.

    Raises:
        Exception: Si el modelo no está disponible o falla la inferencia.
    """
    if not text.strip():
        raise ValueError("synthesize() recibió texto vacío.")

    return await asyncio.to_thread(_synthesize_sync, text)


def cleanup_model() -> None:
    """Libera el modelo de VRAM (útil en pruebas o al apagar el bot)."""
    _load_model.cache_clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Modelo TTS descargado de memoria.")
