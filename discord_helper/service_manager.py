"""Service manager — installs discord-helper as a background service.

Supported:
  Linux  → systemd --user
  macOS  → launchd (LaunchAgents)
  Windows → Task Scheduler (schtasks)
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config_loader import CONFIG_DIR, LOG_DIR

APP_NAME = "discord-helper"
TASK_NAME = "DiscordHelper"

SYSTEMD_DIR = Path.home() / ".config" / "systemd" / "user"
LAUNCHD_DIR = Path.home() / "Library" / "LaunchAgents"

SYSTEMD_FILE = SYSTEMD_DIR / f"{APP_NAME}.service"
LAUNCHD_FILE = LAUNCHD_DIR / f"com.{APP_NAME}.plist"


def _cli_path() -> str:
    """Return the absolute path of the discord-helper CLI binary."""
    path = shutil.which(APP_NAME)
    if path is None:
        # Fallback: common pipx location
        fallback = Path.home() / ".local" / "bin" / APP_NAME
        if fallback.exists():
            return str(fallback)
        # Last resort — let systemd/launchd try PATH
        return APP_NAME
    return path


def install_service() -> str:
    system = platform.system()

    if system == "Linux":
        return _install_systemd()

    if system == "Darwin":
        return _install_launchd()

    if system == "Windows":
        return _install_task_scheduler()

    return f"Unsupported platform: {system}"


def uninstall_service() -> str:
    system = platform.system()

    if system == "Linux":
        if SYSTEMD_FILE.exists():
            SYSTEMD_FILE.unlink()
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=False,
            )
            return "systemd service removed"
        return "systemd service not found"

    if system == "Darwin":
        if LAUNCHD_FILE.exists():
            subprocess.run(
                ["launchctl", "unload", str(LAUNCHD_FILE)],
                check=False,
            )
            LAUNCHD_FILE.unlink()
            return "launchd service removed"
        return "launchd service not found"

    if system == "Windows":
        return _uninstall_task_scheduler()

    return "unsupported platform"


# ── Linux / systemd ────────────────────────────────────────────────────────────

def _install_systemd() -> str:
    SYSTEMD_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    cli = _cli_path()

    service_content = f"""[Unit]
Description=Discord Helper local voice assistant
After=network.target

[Service]
Type=simple
ExecStart={cli} run
Restart=always
RestartSec=5
WorkingDirectory={CONFIG_DIR}
StandardOutput=append:{LOG_DIR / "discord-helper.log"}
StandardError=append:{LOG_DIR / "discord-helper.log"}

[Install]
WantedBy=default.target
"""

    SYSTEMD_FILE.write_text(service_content)

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)

    return (
        f"systemd service installed: {SYSTEMD_FILE}\n"
        "Run: systemctl --user enable --now discord-helper"
    )


# ── macOS / launchd ────────────────────────────────────────────────────────────

def _install_launchd() -> str:
    LAUNCHD_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    cli = _cli_path()
    out_log = str(LOG_DIR / "discord-helper.log")

    # Resolve the PATH that includes pipx bin dir for launchd (which has no shell PATH)
    import os
    env_path = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{APP_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{cli}</string>
        <string>run</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{env_path}</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>{CONFIG_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{out_log}</string>

    <key>StandardErrorPath</key>
    <string>{out_log}</string>
</dict>
</plist>
"""

    LAUNCHD_FILE.write_text(plist_content)

    subprocess.run(
        ["launchctl", "load", str(LAUNCHD_FILE)],
        check=False,
    )

    return f"launchd service installed and loaded: {LAUNCHD_FILE}"


# ── Windows / Task Scheduler ───────────────────────────────────────────────────

def _install_task_scheduler() -> str:
    cli = _cli_path()

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>999</Count>
    </RestartOnFailure>
  </Settings>
  <Actions>
    <Exec>
      <Command>{cli}</Command>
      <Arguments>run</Arguments>
    </Exec>
  </Actions>
</Task>
"""

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".xml",
        encoding="utf-16",
        delete=False,
    ) as f:
        f.write(task_xml)
        xml_path = f.name

    result = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN", TASK_NAME,
            "/XML", xml_path,
            "/F",
        ],
        capture_output=True,
        text=True,
    )

    import os
    try:
        os.unlink(xml_path)
    except OSError:
        pass

    if result.returncode != 0:
        return f"Task Scheduler error: {result.stderr.strip()}"

    return (
        f"Task Scheduler task '{TASK_NAME}' installed.\n"
        "The bot will start automatically on next login.\n"
        "To start it now: schtasks /Run /TN DiscordHelper"
    )


def _uninstall_task_scheduler() -> str:
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return f"Could not remove task: {result.stderr.strip()}"

    return f"Task Scheduler task '{TASK_NAME}' removed."
