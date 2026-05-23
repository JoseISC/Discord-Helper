"""
Configuración del bot — carga valores desde variables de entorno.

No llama a sys.exit() en import time. La validación de vars requeridas
la realiza load_runtime_config(), invocada por discord_helper.runtime.run_bot()
después de que config_loader.load_config() ya cargó el archivo del usuario.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# --- Credenciales y modelos ---
# Estas variables se actualizan cuando load_runtime_config() se llama en runtime.
DISCORD_TOKEN: str = _get("DISCORD_TOKEN")
OLLAMA_MODEL: str = _get("OLLAMA_MODEL", "llama3")
OLLAMA_HOST: str = _get("OLLAMA_HOST", "http://localhost:11434")
WHISPER_MODEL: str = _get("WHISPER_MODEL", "medium")
ASR_LANGUAGE: str | None = os.getenv("ASR_LANGUAGE") or None

# --- TTS ---
TTS_MODEL: str = _get("TTS_MODEL", "facebook/mms-tts-spa")


def load_runtime_config() -> None:
    """Relee las variables de entorno y actualiza el módulo en lugar.

    Debe llamarse después de config_loader.load_config() para que el archivo
    ~/.config/discord-helper/config.env ya esté cargado en el entorno.
    Levanta RuntimeError si faltan vars requeridas.
    """
    global DISCORD_TOKEN, OLLAMA_MODEL, OLLAMA_HOST, WHISPER_MODEL, ASR_LANGUAGE, TTS_MODEL
    global WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, TTS_DEVICE

    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
    ASR_LANGUAGE = os.getenv("ASR_LANGUAGE") or None
    TTS_MODEL = os.getenv("TTS_MODEL", "facebook/mms-tts-spa")

    missing = [k for k in ("DISCORD_TOKEN", "OLLAMA_MODEL") if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            "Faltan variables requeridas: "
            + ", ".join(missing)
            + ". Ejecuta: discord-helper setup"
        )

    WHISPER_DEVICE, WHISPER_COMPUTE_TYPE = _detect_device()
    TTS_DEVICE = _detect_tts_device()

    logger.info(
        "Configuración cargada: model=%s host=%s whisper=%s(%s/%s) tts=%s(%s)",
        OLLAMA_MODEL,
        OLLAMA_HOST,
        WHISPER_MODEL,
        WHISPER_DEVICE,
        WHISPER_COMPUTE_TYPE,
        TTS_MODEL,
        TTS_DEVICE,
    )


# --- Detección de CUDA ---

def _detect_device() -> tuple[str, str]:
    """Devuelve (device, compute_type) según la disponibilidad de GPU CUDA."""
    try:
        import ctranslate2  # type: ignore[import]

        if ctranslate2.get_cuda_device_count() > 0:
            logger.info("CUDA detectado: usando GPU con compute_type=float16")
            return "cuda", "float16"
    except Exception:
        pass

    logger.warning(
        "CUDA no disponible o ctranslate2 no instalado. Usando CPU con compute_type=int8."
    )
    return "cpu", "int8"


def _detect_tts_device() -> str:
    if os.getenv("TTS_FORCE_CPU", "").strip() == "1":
        logger.info("TTS forzado a CPU por TTS_FORCE_CPU=1.")
        return "cpu"
    try:
        import torch  # type: ignore[import]

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


# Valores por defecto en tiempo de import (se sobreescriben por load_runtime_config)
WHISPER_DEVICE, WHISPER_COMPUTE_TYPE = _detect_device()
TTS_DEVICE: str = _detect_tts_device()
