from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config_loader import CONFIG_FILE, LOG_DIR, load_config
from .platform_utils import detect_nvidia_smi, detect_ollama, get_platform_info

BASE_DIR = Path(__file__).resolve().parent.parent
GUI_DIR = BASE_DIR / "gui"

app = FastAPI(title="Discord Helper GUI Server")

if GUI_DIR.exists():
    app.mount("/assets", StaticFiles(directory=GUI_DIR), name="assets")


@app.get("/")
def index():
    return FileResponse(GUI_DIR / "index.html")


@app.get("/api/status")
def status():
    load_config()
    platform_info = get_platform_info()
    ollama = detect_ollama()

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
            "model": os.getenv("OLLAMA_MODEL"),
            "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "discord_token_configured": bool(os.getenv("DISCORD_TOKEN")),
        },
        "dependencies": {
            "ffmpeg": shutil.which("ffmpeg"),
            "ollama_binary": ollama["binary"],
            "ollama_server_running": ollama["server_running"],
            "nvidia_smi": detect_nvidia_smi(),
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
    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        timeout=5,
    ) if shutil.which("ollama") else None

    if result is None or result.returncode != 0:
        return {"ok": False, "models": []}

    rows = result.stdout.splitlines()[1:]
    names = [row.split()[0] for row in rows if row.strip()]

    return {"ok": True, "models": names}


def serve(host: str = "127.0.0.1", port: int = 8750) -> None:
    import uvicorn

    uvicorn.run("discord_helper.gui_server:app", host=host, port=port, reload=False)
