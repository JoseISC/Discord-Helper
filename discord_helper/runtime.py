from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys

from .config_loader import load_config
from .logging_utils import configure_logging

logger = logging.getLogger(__name__)


class RuntimeManager:
    def __init__(self) -> None:
        self.process: asyncio.subprocess.Process | None = None

    async def launch(self) -> None:
        logger.info("Starting Discord Helper runtime")

        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "main.py",
        )

        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self.shutdown(s)),
            )

        await self.process.wait()

    async def shutdown(self, sig: signal.Signals) -> None:
        logger.info("Received signal: %s", sig.name)

        if self.process:
            self.process.terminate()
            await self.process.wait()

        logger.info("Discord Helper stopped gracefully")
        raise SystemExit(0)



def run_bot() -> None:
    load_config()
    configure_logging()

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

    runtime = RuntimeManager()

    asyncio.run(runtime.launch())
