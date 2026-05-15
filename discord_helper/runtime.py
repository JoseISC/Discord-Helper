from __future__ import annotations

import asyncio
import os
import subprocess
import sys

from .config_loader import load_config


def run_bot() -> None:
    load_config()

    required = [
        "DISCORD_TOKEN",
        "OLLAMA_MODEL",
    ]

    missing = [key for key in required if not os.getenv(key)]

    if missing:
        print("Missing required configuration:")
        for item in missing:
            print(f" - {item}")
        print("Run: discord-helper setup")
        raise SystemExit(1)

    asyncio.run(_launch())


async def _launch() -> None:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "main.py",
    )

    await process.wait()
