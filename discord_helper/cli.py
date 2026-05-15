from __future__ import annotations

import os
import shutil
import sys
import webbrowser

import typer

from .config_loader import CONFIG_FILE
from .config_loader import LOG_DIR
from .config_loader import load_config
from .config_loader import save_config
from .gui_server import serve as serve_gui
from .platform_utils import detect_nvidia_smi
from .platform_utils import detect_ollama
from .platform_utils import get_platform_info
from .runtime import run_bot
from .service_manager import install_service as install_local_service
from .service_manager import uninstall_service as uninstall_local_service

app = typer.Typer(help="Discord Helper CLI")


@app.command()
def setup():
    typer.echo("Discord Helper Setup")

    discord_token = typer.prompt("Discord bot token")
    ollama_model = typer.prompt("Ollama model", default="llama3")
    ollama_host = typer.prompt("Ollama host", default="http://localhost:11434")
    whisper_model = typer.prompt("Whisper model", default="medium")

    save_config(
        {
            "DISCORD_TOKEN": discord_token,
            "OLLAMA_MODEL": ollama_model,
            "OLLAMA_HOST": ollama_host,
            "WHISPER_MODEL": whisper_model,
        }
    )

    typer.echo(f"Configuration saved to: {CONFIG_FILE}")


@app.command()
def doctor():
    load_config()

    typer.echo("Running diagnostics...\n")

    _check_platform()
    _check_python()
    _check_ffmpeg()
    _check_ollama()
    _check_cuda()
    _check_config()
    _check_logs()


@app.command()
def run():
    run_bot()


@app.command()
def gui(host: str = "127.0.0.1", port: int = 8750, open_browser: bool = True):
    """Start GUI runtime server."""

    url = f"http://{host}:{port}"

    typer.echo(f"Starting GUI server at {url}")

    if open_browser:
        webbrowser.open(url)

    serve_gui(host=host, port=port)


@app.command(name="open-gui")
def open_gui():
    webbrowser.open("http://127.0.0.1:8750")


@app.command(name="install-service")
def install_service():
    result = install_local_service()
    typer.echo(result)


@app.command(name="uninstall-service")
def uninstall_service():
    result = uninstall_local_service()
    typer.echo(result)


@app.command()
def logs():
    typer.echo(f"Logs directory: {LOG_DIR}")


@app.command()
def discord_guide():
    typer.echo("Discord Developer Portal:")
    typer.echo("https://discord.com/developers/applications")


@app.command()
def update():
    typer.echo("Update feature planned for future release")


@app.command()
def version():
    typer.echo("discord-helper 0.7.0")


# Diagnostics


def _check_platform() -> None:
    info = get_platform_info()

    typer.echo(f"Platform: {info.system} {info.release} ({info.machine})")

    if info.is_windows:
        typer.echo("Windows compatibility layer: ENABLED")



def _check_python() -> None:
    typer.echo(f"Python: {sys.version.split()[0]}")



def _check_ffmpeg() -> None:
    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg:
        typer.echo(f"FFmpeg: OK ({ffmpeg})")
    else:
        typer.echo("FFmpeg: NOT FOUND")



def _check_ollama() -> None:
    ollama = detect_ollama()

    if not ollama["binary"]:
        typer.echo("Ollama: NOT FOUND")
        return

    typer.echo(f"Ollama binary: {ollama['binary']}")

    if ollama["server_running"]:
        typer.echo("Ollama server: OK")
    else:
        typer.echo("Ollama server: OFFLINE")



def _check_cuda() -> None:
    nvidia_smi = detect_nvidia_smi()

    if nvidia_smi:
        typer.echo(f"CUDA/NVIDIA: OK ({nvidia_smi})")
    else:
        typer.echo("CUDA/NVIDIA: NOT DETECTED")



def _check_config() -> None:
    required = ["DISCORD_TOKEN", "OLLAMA_MODEL"]

    missing: list[str] = []

    for key in required:
        if not os.getenv(key):
            missing.append(key)

    if missing:
        typer.echo("Missing config:")
        for item in missing:
            typer.echo(f" - {item}")
    else:
        typer.echo("Configuration: OK")



def _check_logs() -> None:
    if LOG_DIR.exists():
        typer.echo(f"Logs directory: OK ({LOG_DIR})")
    else:
        typer.echo("Logs directory: NOT FOUND")


if __name__ == "__main__":
    app()
