"""TTS runtime with async lazy loading and CUDA-to-CPU fallback."""

import asyncio
import logging
import os
import tempfile
import wave

import numpy as np
import torch
from transformers import AutoTokenizer, VitsModel

from . import config

logger = logging.getLogger(__name__)

_active_device: str = config.TTS_DEVICE
_model = None
_tokenizer = None
_model_lock = asyncio.Lock()


async def get_model():
    """Load the TTS model once per process without blocking the event loop."""
    global _model, _tokenizer

    if _model is not None:
        return _model, _tokenizer

    async with _model_lock:
        if _model is None:
            _model, _tokenizer = await asyncio.to_thread(_load_sync)

    return _model, _tokenizer


def _load_sync():
    logger.info("Loading TTS model %s on %s", config.TTS_MODEL, _active_device)

    model = VitsModel.from_pretrained(config.TTS_MODEL)
    model = model.to(_active_device)
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(config.TTS_MODEL)

    return model, tokenizer


async def synthesize(text: str) -> str:
    """Synthesize text into a temporary WAV file.

    The caller may pass the resulting path to audio.play_wav(). The audio module
    owns final cleanup after playback.
    """
    if not text.strip():
        raise ValueError("synthesize() received empty text")

    model, tokenizer = await get_model()

    try:
        return await asyncio.to_thread(_synthesize_sync, model, tokenizer, text)
    except Exception as exc:
        return await _fallback_to_cpu_and_retry(text, exc)


async def _fallback_to_cpu_and_retry(text: str, original_error: Exception) -> str:
    """Fallback to CPU if GPU inference fails.

    This preserves the original CUDA to CPU behavior while keeping the lazy async
    singleton pattern introduced in Sprint 4.
    """
    global _active_device, _model, _tokenizer

    if _active_device == "cpu":
        raise original_error

    logger.warning(
        "TTS inference failed on %s: %s. Falling back to CPU.",
        _active_device,
        original_error,
    )

    async with _model_lock:
        _active_device = "cpu"
        _model = None
        _tokenizer = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        _model, _tokenizer = await asyncio.to_thread(_load_sync)

    return await asyncio.to_thread(_synthesize_sync, _model, _tokenizer, text)


def _synthesize_sync(model, tokenizer, text: str) -> str:
    inputs = tokenizer(text, return_tensors="pt")
    inputs = {k: v.to(_active_device) for k, v in inputs.items()}

    with torch.no_grad():
        output = model(**inputs)

    waveform: np.ndarray = output.waveform.squeeze().cpu().numpy()
    pcm16 = (waveform * 32767.0).clip(-32768, 32767).astype(np.int16)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(model.config.sampling_rate)
            wf.writeframes(pcm16.tobytes())

        return tmp_path

    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def cleanup_model() -> None:
    """Release loaded TTS model memory."""
    global _model, _tokenizer

    _model = None
    _tokenizer = None

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
