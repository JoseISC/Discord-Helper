"""
AmlaBot — entry point del bot de Discord.

Usa discord.py 2.7+ que incluye soporte nativo para DAVE/E2EE
(protocolo obligatorio en Discord desde marzo de 2026).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys


def _preload_cuda_libs() -> None:
    import ctypes
    import glob
    import importlib.util

    candidates: list[str] = []

    pkg_lib_paths = (
        "nvidia.cublas.lib",
        "nvidia.cudnn.lib",
        "nvidia.cuda_nvrtc.lib",
    )
    for pkg in pkg_lib_paths:
        try:
            mod = __import__(pkg, fromlist=["__path__"])
        except ImportError:
            continue
        lib_dirs = list(getattr(mod, "__path__", []) or [])
        if not lib_dirs and getattr(mod, "__file__", None):
            lib_dirs = [os.path.dirname(mod.__file__)]
        for lib_dir in lib_dirs:
            for so in sorted(glob.glob(os.path.join(lib_dir, "lib*.so*"))):
                candidates.append(so)

    for top_pkg, subdir in (("nvidia.cu13", "lib"),):
        try:
            spec = importlib.util.find_spec(top_pkg)
        except ModuleNotFoundError:
            continue
        if spec is None or spec.submodule_search_locations is None:
            continue
        for root in spec.submodule_search_locations:
            lib_dir = os.path.join(root, subdir)
            if not os.path.isdir(lib_dir):
                continue
            for so in sorted(glob.glob(os.path.join(lib_dir, "lib*.so*"))):
                candidates.append(so)

    for so in candidates:
        try:
            import ctypes
            ctypes.CDLL(so, mode=ctypes.RTLD_GLOBAL)
        except OSError:
            pass


_preload_cuda_libs()

import discord  # noqa: E402
from discord.ext import commands  # noqa: E402

from discord_helper.core import asr, tts  # noqa: E402
from discord_helper.core import config as core_config  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

EXTENSIONS = [
    "discord_helper.cogs.voice",
    "discord_helper.cogs.chat",
]


class AmlaBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.voice_states = True
        intents.guilds = True
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        for ext in EXTENSIONS:
            await self.load_extension(ext)
            logger.info("Extensión cargada: %s", ext)

        await self.tree.sync()
        logger.info("Slash commands sincronizados.")

        asyncio.create_task(asr.get_model())
        asyncio.create_task(tts.get_model())

        logger.info("Background model preload started")

    async def on_ready(self) -> None:
        logger.info("Bot conectado como %s (ID: %s)", self.user, self.user.id)
        logger.info("Servidores: %d", len(self.guilds))

    async def on_application_command_error(
        self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ) -> None:
        logger.error("Error en comando '%s': %s", interaction.command, error)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Ocurrió un error inesperado. Revisa los logs del bot.", ephemeral=True
            )


async def main() -> None:
    async with AmlaBot() as bot:
        logger.info("Iniciando bot...")
        await bot.start(core_config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
