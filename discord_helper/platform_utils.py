from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformInfo:
    system: str
    release: str
    machine: str
    is_windows: bool
    is_linux: bool
    is_macos: bool


def get_platform_info() -> PlatformInfo:
    system = platform.system()

    return PlatformInfo(
        system=system,
        release=platform.release(),
        machine=platform.machine(),
        is_windows=system == "Windows",
        is_linux=system == "Linux",
        is_macos=system == "Darwin",
    )


def find_executable(name: str) -> str | None:
    return shutil.which(name)


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def detect_ollama() -> dict[str, str | bool | None]:
    exe = find_executable("ollama")
    server = is_port_open("127.0.0.1", 11434)

    return {
        "binary": exe,
        "server_running": server,
        "default_host": "http://localhost:11434",
    }


def detect_nvidia_smi() -> str | None:
    return find_executable("nvidia-smi")


def run_command(command: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return None


def get_windows_local_bin_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".local", "bin", "discord-helper")
