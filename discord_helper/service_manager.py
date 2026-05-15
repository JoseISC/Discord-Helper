from __future__ import annotations

import platform
from pathlib import Path

from .config_loader import CONFIG_DIR

APP_NAME = "discord-helper"

SYSTEMD_DIR = Path.home() / ".config" / "systemd" / "user"
LAUNCHD_DIR = Path.home() / "Library" / "LaunchAgents"

SYSTEMD_FILE = SYSTEMD_DIR / f"{APP_NAME}.service"
LAUNCHD_FILE = LAUNCHD_DIR / f"com.{APP_NAME}.plist"


def install_service() -> str:
    system = platform.system()

    if system == "Linux":
        return _install_systemd()

    if system == "Darwin":
        return _install_launchd()

    return f"Unsupported platform: {system}"



def uninstall_service() -> str:
    system = platform.system()

    if system == "Linux":
        if SYSTEMD_FILE.exists():
            SYSTEMD_FILE.unlink()
            return "systemd service removed"
        return "systemd service not found"

    if system == "Darwin":
        if LAUNCHD_FILE.exists():
            LAUNCHD_FILE.unlink()
            return "launchd service removed"
        return "launchd service not found"

    return "unsupported platform"



def _install_systemd() -> str:
    SYSTEMD_DIR.mkdir(parents=True, exist_ok=True)

    service_content = f"""[Unit]
Description=Discord Helper
After=network.target

[Service]
Type=simple
ExecStart=discord-helper run
Restart=always
RestartSec=5
WorkingDirectory={CONFIG_DIR}

[Install]
WantedBy=default.target
"""

    SYSTEMD_FILE.write_text(service_content)

    return f"systemd service installed: {SYSTEMD_FILE}"



def _install_launchd() -> str:
    LAUNCHD_DIR.mkdir(parents=True, exist_ok=True)

    plist_content = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
    <key>Label</key>
    <string>com.discord-helper</string>

    <key>ProgramArguments</key>
    <array>
        <string>discord-helper</string>
        <string>run</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""

    LAUNCHD_FILE.write_text(plist_content)

    return f"launchd service installed: {LAUNCHD_FILE}"
