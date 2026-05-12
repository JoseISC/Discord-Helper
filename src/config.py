"""
Carga y valida la configuración del bot desde el archivo .env.
Verifica disponibilidad de CUDA para el motor ASR.
"""

import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        logger.critical("Variable de entorno requerida '%s' no está definida. Revisa tu .env", key)
        sys.exit(1)
    return value


# --- Credenciales y modelos ---
DISCORD_TOKEN: str = _require("DISCORD_TOKEN")
OLLAMA_MODEL: str = _require("OLLAMA_MODEL")
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "medium")
ASR_LANGUAGE: str | None = os.getenv("ASR_LANGUAGE") or None  # None → auto-detección

# --- TTS ---
TTS_MODEL: str = os.getenv("TTS_MODEL", "facebook/mms-tts-spa")


# --- Detección de CUDA ---
def _detect_device() -> tuple[str, str]:
    """
    Devuelve (device, compute_type) según la disponibilidad de GPU CUDA.
    Prioriza float16 en GPU; cae a int8 en CPU como fallback seguro.
    """
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            logger.info("CUDA detectado: usando GPU con compute_type=float16")
            return "cuda", "float16"
    except Exception:
        pass

    logger.warning(
        "CUDA no disponible o ctranslate2 no instalado correctamente. "
        "Usando CPU con compute_type=int8 (más lento)."
    )
    return "cpu", "int8"


WHISPER_DEVICE, WHISPER_COMPUTE_TYPE = _detect_device()

# Device para el modelo TTS (torch).
# Si TTS_FORCE_CPU=1 está definida, usa CPU independientemente de la GPU.
# Esto permite liberar VRAM para Whisper si la GPU es pequeña.
if os.getenv("TTS_FORCE_CPU", "").strip() == "1":
    TTS_DEVICE = "cpu"
    logger.info("TTS forzado a CPU por TTS_FORCE_CPU=1.")
else:
    try:
        import torch
        TTS_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        TTS_DEVICE = "cpu"
    logger.info("TTS usará device=%s.", TTS_DEVICE)
