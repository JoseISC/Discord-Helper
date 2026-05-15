from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer

from .config_loader import CONFIG_FILE
from .config_loader import LOG_DIR
from .config_loader import load_config
from .config_loader import save_config
from .platform_utils import detect_nvidia_smi
from .platform_utils import detect_ollama
from .platform_utils import get_platform_info
from .runtime import run_bot
from .service_manager import install_service as install_local_service
from .service_manager import uninstall_service as uninstall_local_service

app = typer.Typer(help="Discord Helper CLI")


@app.command()
def setup():
    """Interactive setup wizard."""

    typer.echo("Discord Helper Setup")

    discord_token = typer.prompt("Discord bot token")
    ollama_model = typer.prompt("Ollama model", default="llama3")
    ollama_host = typer.prompt(
        "Ollama host",
        default="http://localhost:11434",
    )
    whisper_model = typer.prompt(
        "Whisper model",
        default="medium",
    )

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
    """Validate local environment."""

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
    """Run Discord Helper bot."""

    run_bot()


@app.command(name="install-service")
def install_service():
    """Install local background service."""

    result = install_local_service()
    typer.echo(result)


@app.command(name="uninstall-service")
def uninstall_service():
    """Remove local background service."""

    result = uninstall_local_service()
    typer.echo(result)


@app.command()
def logs():
    """Show application logs."""

    typer.echo(f"Logs directory: {LOG_DIR}")

    log_file = LOG_DIR / "discord-helper.log"

    if log_file.exists():
        typer.echo(f"Main log file: {log_file}")
    else:
        typer.echo("No logs generated yet")


@app.command()
def discord_guide():
    """Show Discord onboarding guide."""

    typer.echo("Discord Developer Portal:")
    typer.echo("https://discord.com/developers/applications")
    typer.echo("")
    typer.echo("See full guide in docs/discord-setup.md")


@app.command()
def update():
    """Update Discord Helper source."""

    typer.echo("Update feature planned for future release")


@app.command()
def version():
    """Show version."""

    typer.echo("discord-helper 0.4.0")


def _check_platform() -> None:
    info = get_platform_info()

    typer.echo(f"Platform: {info.system} {info.release} ({info.machine})")

    if info.is_windows:
        typer.echo("Windows compatibility layer: ENABLED")


# ------------------------------------------------------------------
# Diagnostics
# ------------------------------------------------------------------


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
    required = [
        "DISCORD_TOKEN",
        "OLLAMA_MODEL",
    ]

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
