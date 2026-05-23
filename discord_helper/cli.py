from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import webbrowser

import typer

from . import __version__
from .config_loader import CONFIG_FILE, LOG_DIR, load_config, save_config
from .gui_server import serve as serve_gui
from .platform_utils import detect_nvidia_smi, detect_ollama, get_platform_info
from .runtime import run_bot
from .service_manager import install_service as install_local_service
from .service_manager import uninstall_service as uninstall_local_service

app = typer.Typer(help="Discord Helper CLI — local voice AI assistant")

# Install dir written by install.sh / install.ps1
_INSTALL_DIR = os.path.expanduser(
    os.path.join(
        os.environ.get("LOCALAPPDATA", "~"),
        "discord-helper",
        "source",
    )
    if platform.system() == "Windows"
    else os.path.join("~", ".local", "share", "discord-helper", "source")
)


@app.command()
def setup():
    """Interactive wizard: configure token, models and persist to config file."""
    typer.echo("Discord Helper Setup")
    typer.echo("=" * 40)

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

    # Restrict config file permissions (token is sensitive)
    try:
        CONFIG_FILE.chmod(0o600)
    except Exception:
        pass  # Windows doesn't support chmod — silently skip

    typer.echo(f"\nConfiguration saved to: {CONFIG_FILE}")
    typer.echo("Run 'discord-helper doctor' to verify your setup.")


@app.command()
def doctor():
    """Diagnose the installation and report any missing dependencies."""
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
    """Start the Discord bot."""
    run_bot()


@app.command()
def gui(
    host: str = typer.Option("127.0.0.1", help="Bind address"),
    port: int = typer.Option(8750, help="Port"),
    open_browser: bool = typer.Option(True, help="Open browser on start"),
):
    """Start the local GUI dashboard server."""
    url = f"http://{host}:{port}"
    typer.echo(f"Starting GUI server at {url}")

    if open_browser:
        webbrowser.open(url)

    serve_gui(host=host, port=port)


@app.command(name="open-gui")
def open_gui():
    """Open the GUI in the default browser (server must already be running)."""
    webbrowser.open("http://127.0.0.1:8750")


@app.command(name="install-service")
def install_service():
    """Install discord-helper as a background service (systemd / launchd / Task Scheduler)."""
    result = install_local_service()
    typer.echo(result)


@app.command(name="uninstall-service")
def uninstall_service():
    """Remove the background service."""
    result = uninstall_local_service()
    typer.echo(result)


@app.command()
def logs():
    """Show the path to the runtime log directory."""
    typer.echo(f"Logs directory: {LOG_DIR}")
    log_file = LOG_DIR / "discord-helper.log"
    if log_file.exists():
        typer.echo(f"Main log:       {log_file}")
    else:
        typer.echo("No log file yet. Run 'discord-helper run' first.")


@app.command(name="discord-guide")
def discord_guide():
    """Open the Discord developer portal and show bot setup instructions."""
    typer.echo("Discord Developer Portal: https://discord.com/developers/applications")
    typer.echo("\nSteps:")
    typer.echo("  1. New Application -> Bot -> Add Bot")
    typer.echo("  2. Enable: Message Content Intent, Server Members Intent")
    typer.echo("  3. Copy token -> run 'discord-helper setup'")
    typer.echo("  4. OAuth2 -> URL Generator (scopes: bot, applications.commands)")
    typer.echo("  5. Invite URL -> open in browser")


@app.command()
def update():
    """Pull the latest source and reinstall via pipx."""
    install_dir = os.path.expanduser(_INSTALL_DIR)

    if not os.path.isdir(os.path.join(install_dir, ".git")):
        typer.echo(f"Source directory not found at {install_dir}")
        typer.echo("Re-run the installer: curl -fsSL <URL>/install.sh | bash")
        raise typer.Exit(1)

    typer.echo(f"Pulling latest changes from {install_dir} ...")
    subprocess.run(["git", "-C", install_dir, "pull"], check=True)

    typer.echo("Reinstalling via pipx ...")
    subprocess.run(["pipx", "reinstall", "discord-helper"], check=True)

    typer.echo("Update complete. Run 'discord-helper version' to verify.")


@app.command()
def version():
    """Print the installed version."""
    typer.echo(f"discord-helper {__version__}")


# ── diagnostics ────────────────────────────────────────────────────────────────

def _check_platform() -> None:
    info = get_platform_info()
    typer.echo(f"Platform: {info.system} {info.release} ({info.machine})")
    if info.is_windows:
        typer.echo("Windows compatibility: ENABLED")


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

    if not ollama["server_running"]:
        typer.echo("Ollama server: OFFLINE")
        return

    typer.echo("Ollama server: OK")

    # Validate that the configured model is available
    configured_model = os.getenv("OLLAMA_MODEL", "")
    if configured_model:
        _check_ollama_model(configured_model)


def _check_ollama_model(model: str) -> None:
    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    if result.returncode != 0:
        typer.echo(f"Ollama models: could not list ({result.stderr.strip()})")
        return

    rows = result.stdout.splitlines()[1:]
    available = [row.split()[0] for row in rows if row.strip()]

    if not available:
        typer.echo("Ollama models: none pulled yet. Run: ollama pull <model>")
        return

    if any(m.startswith(model.split(":")[0]) for m in available):
        typer.echo(f"Ollama model '{model}': OK")
    else:
        typer.echo(f"Ollama model '{model}': NOT FOUND (available: {', '.join(available[:5])})")
        typer.echo(f"  Run: ollama pull {model}")


def _check_cuda() -> None:
    nvidia_smi = detect_nvidia_smi()
    if nvidia_smi:
        typer.echo(f"CUDA/NVIDIA: OK ({nvidia_smi})")
    else:
        typer.echo("CUDA/NVIDIA: NOT DETECTED (CPU mode)")


def _check_config() -> None:
    required = ["DISCORD_TOKEN", "OLLAMA_MODEL"]
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        typer.echo("Configuration: INCOMPLETE")
        for item in missing:
            typer.echo(f"  Missing: {item}")
        typer.echo("  Run: discord-helper setup")
    else:
        typer.echo("Configuration: OK")


def _check_logs() -> None:
    if LOG_DIR.exists():
        typer.echo(f"Logs directory: OK ({LOG_DIR})")
    else:
        typer.echo("Logs directory: NOT FOUND (will be created on first run)")


if __name__ == "__main__":
    app()
