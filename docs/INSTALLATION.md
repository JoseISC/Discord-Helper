# Discord Helper — Installation Guide

## Quick Install

### Linux / macOS

```bash
curl -fsSL https://raw.githubusercontent.com/JoseISC/Discord-Helper/instalador/scripts/install.sh | bash
```

The script:
- Checks Python 3.10+, git, pipx
- Detects NVIDIA GPU and installs `[cuda]` extras automatically
- Installs FFmpeg via your system package manager
- Clones the repo to `~/.local/share/discord-helper/source`
- Installs the CLI via `pipx`

### Windows

```powershell
iwr -useb https://raw.githubusercontent.com/JoseISC/Discord-Helper/instalador/scripts/install.ps1 | iex
```

See `docs/WINDOWS.md` for manual steps.

### Advanced — pip / pipx

CPU-only:
```bash
pipx install "discord-helper @ git+https://github.com/JoseISC/Discord-Helper@instalador"
```

With CUDA:
```bash
pipx install "discord-helper[cuda] @ git+https://github.com/JoseISC/Discord-Helper@instalador"
```

---

## After Installation

```bash
discord-helper setup
```

You will be prompted for:
- Discord bot token (from https://discord.com/developers/applications)
- Ollama model name (e.g. `llama3`)
- Ollama host (default: `http://localhost:11434`)
- Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`)

Then:

```bash
discord-helper doctor    # verify all dependencies
discord-helper run       # start the bot
```

---

## Optional: Background Service

### Linux

```bash
discord-helper install-service
systemctl --user enable --now discord-helper
```

### macOS

```bash
discord-helper install-service
```

Service auto-starts on login via launchd.

### Windows

```bash
discord-helper install-service
```

Creates a Task Scheduler task that runs on login.

---

## GUI Dashboard

```bash
discord-helper gui
```

Opens `http://127.0.0.1:8750` — a retro XP-style local dashboard.

---

## Uninstall

```bash
discord-helper uninstall-service    # remove service (if installed)
pipx uninstall discord-helper
```

---

## Logs

```bash
discord-helper logs
# → ~/.local/share/discord-helper/logs/discord-helper.log
```

---

## Configuration file

```
~/.config/discord-helper/config.env
```

Permissions are set to `0600` (owner read/write only) by `discord-helper setup`.

---

## Supported Platforms

| Platform | Tested | Notes |
|----------|--------|-------|
| Ubuntu 22.04+ | Yes | Primary dev platform |
| Fedora 38+ | Yes | |
| Arch Linux | Yes | |
| macOS 13+ | Experimental | CPU-only TTS |
| Windows 10/11 | Experimental | Requires Python 3.10+, git, winget |
