"""FastAPI server that serves the GUI and exposes runtime status APIs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config_loader import CONFIG_FILE, LOG_DIR, load_config
from .platform_utils import detect_nvidia_smi, detect_ollama, get_platform_info

# GUI files live inside the installed package, not the repo root.
GUI_DIR = Path(__file__).resolve().parent / "gui"

# Runtime state written by bot.py every few seconds.
RUNTIME_STATE_FILE = LOG_DIR.parent / "runtime-state.json"

app = FastAPI(title="Discord Helper GUI Server")

if GUI_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(GUI_DIR / "assets")), name="assets")
    app.mount("/static", StaticFiles(directory=str(GUI_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(GUI_DIR / "index.html")


@app.get("/styles.css")
def styles():
    return FileResponse(GUI_DIR / "styles.css", media_type="text/css")


@app.get("/runtime.js")
def runtime_js():
    return FileResponse(GUI_DIR / "runtime.js", media_type="application/javascript")


def _read_runtime_state() -> dict:
    try:
        if RUNTIME_STATE_FILE.exists():
            return json.loads(RUNTIME_STATE_FILE.read_text())
    except Exception:
        pass
    return {}


@app.get("/api/status")
def status():
    load_config()
    platform_info = get_platform_info()
    ollama = detect_ollama()
    state = _read_runtime_state()

    whisper_model = os.getenv("WHISPER_MODEL", "medium")
    ollama_model = os.getenv("OLLAMA_MODEL", "")
    tts_model = os.getenv("TTS_MODEL", "facebook/mms-tts-spa")

    return {
        "app": "Discord Helper",
        "version": "0.7.0",
        "platform": {
            "system": platform_info.system,
            "release": platform_info.release,
            "machine": platform_info.machine,
        },
        "config": {
            "exists": CONFIG_FILE.exists(),
            "model": ollama_model,
            "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "discord_token_configured": bool(os.getenv("DISCORD_TOKEN")),
        },
        "dependencies": {
            "ffmpeg": shutil.which("ffmpeg"),
            "ollama_binary": ollama["binary"],
            "ollama_server_running": ollama["server_running"],
            "nvidia_smi": detect_nvidia_smi(),
        },
        "runtime_stack": {
            "stt": whisper_model,
            "llm": ollama_model or "not configured",
            "tts": tts_model,
            "audio": "FFmpeg",
        },
        "bot": {
            "connected": state.get("connected", False),
            "uptime_seconds": state.get("uptime_seconds", 0),
            "guilds_count": state.get("guilds_count", 0),
            "slash_commands": state.get("slash_commands", 6),
        },
    }


@app.get("/api/logs")
def logs(lines: int = 80):
    log_file = LOG_DIR / "discord-helper.log"

    if not log_file.exists():
        return {"exists": False, "lines": []}

    content = log_file.read_text(errors="ignore").splitlines()
    return {"exists": True, "lines": content[-lines:]}


@app.get("/api/models")
def models():
    result = (
        subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if shutil.which("ollama")
        else None
    )

    if result is None or result.returncode != 0:
        return {"ok": False, "models": []}

    rows = result.stdout.splitlines()[1:]
    names = [row.split()[0] for row in rows if row.strip()]

    return {"ok": True, "models": names}


def serve(host: str = "127.0.0.1", port: int = 8750) -> None:
    import uvicorn

    uvicorn.run("discord_helper.gui_server:app", host=host, port=port, reload=False)
