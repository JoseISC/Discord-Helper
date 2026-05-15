"""Sprint 4 TTS runtime improvements."""

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
    global _model, _tokenizer

    if _model is not None:
        return _model, _tokenizer

    async with _model_lock:
        if _model is None:
            _model, _tokenizer = await asyncio.to_thread(_load_sync)

    return _model, _tokenizer



def _load_sync():
    logger.info("Loading TTS model %s", config.TTS_MODEL)

    model = VitsModel.from_pretrained(config.TTS_MODEL)
    model = model.to(_active_device)
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(config.TTS_MODEL)

    return model, tokenizer


async def synthesize(text: str) -> str:
    model, tokenizer = await get_model()

    return await asyncio.to_thread(_synthesize_sync, model, tokenizer, text)



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
