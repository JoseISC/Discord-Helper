"""
Módulo de reproducción de audio en canales de voz de Discord.

Gestiona una cola de reproducción por guild para evitar que varias respuestas TTS
se solapen. El archivo WAV temporal se elimina automáticamente tras reproducirse.
"""

import asyncio
import logging
import os

import discord

logger = logging.getLogger(__name__)

_guild_locks: dict[int, asyncio.Lock] = {}


def _get_lock(guild_id: int) -> asyncio.Lock:
    if guild_id not in _guild_locks:
        _guild_locks[guild_id] = asyncio.Lock()
    return _guild_locks[guild_id]


async def play_wav(vc: discord.VoiceClient, wav_path: str) -> None:
    """Reproduce `wav_path` en el canal de voz `vc` y espera hasta que termine.

    - Serializa reproducciones por guild.
    - Elimina el archivo temporal al terminar (o si ocurre un error).
    """
    if not vc.is_connected():
        try:
            os.unlink(wav_path)
        except OSError:
            pass
        raise RuntimeError("El bot no está conectado a un canal de voz.")

    async with _get_lock(vc.guild.id):
        done = asyncio.Event()
        loop = asyncio.get_running_loop()

        def _after(error: Exception | None) -> None:
            try:
                os.unlink(wav_path)
                logger.debug("Archivo temporal eliminado: %s", wav_path)
            except OSError as exc:
                logger.warning("No se pudo eliminar %s: %s", wav_path, exc)

            if error:
                logger.error("Error durante la reproducción de audio: %s", error)

            loop.call_soon_threadsafe(done.set)

        if vc.is_playing():
            vc.stop()

        source = discord.FFmpegPCMAudio(wav_path)
        vc.play(source, after=_after)
        logger.debug("Reproduciendo %s en guild %s ...", wav_path, vc.guild.id)

        await done.wait()
        logger.debug("Reproducción finalizada en guild %s.", vc.guild.id)
