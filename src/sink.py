"""
AudioSink personalizado para discord-ext-voice-recv.

Captura el audio PCM por usuario y, al finalizar la grabación,
invoca un callback asíncrono con los buffers WAV listos para ASR.

Discord envía PCM a 48kHz estéreo de 16 bits.
"""

import asyncio
import io
import logging
import wave
from typing import Callable, Awaitable, Optional

import discord
from discord.ext import voice_recv
from discord.ext.voice_recv.rtp import FakePacket, SilencePacket

logger = logging.getLogger(__name__)

SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2  # 16-bit PCM

# Tamaño esperado de un frame Opus decodificado (20ms @ 48kHz stéreo 16-bit)
EXPECTED_FRAME_BYTES = int(SAMPLE_RATE * 0.02) * CHANNELS * SAMPLE_WIDTH  # 3840

# Tope de seguridad: cuántos segundos de audio acumular como máximo por usuario.
# Evita memory blow-up si algo va mal con la generación PLC/FEC de la librería.
MAX_BUFFER_SECONDS = 300  # 5 minutos
MAX_BUFFER_BYTES = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * MAX_BUFFER_SECONDS


class WaveSink(voice_recv.AudioSink):
    """
    Acumula PCM por usuario en memoria.
    Al llamar a VoiceRecvClient.stop_listening(), discord-ext-voice-recv invoca cleanup(),
    que dispara el callback con un dict {user_id: BytesIO(WAV)}.
    """

    def __init__(self) -> None:
        super().__init__()
        self._buffers: dict[int, bytearray] = {}
        self._packet_counts: dict[int, int] = {}
        self._fake_packet_counts: dict[int, int] = {}
        self._callback: Callable[[dict[int, io.BytesIO]], Awaitable[None]] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._closed: bool = False

    def set_callback(
        self,
        callback: Callable[[dict[int, io.BytesIO]], Awaitable[None]],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._callback = callback
        self._loop = loop

    # ------------------------------------------------------------------
    # Overrides de voice_recv.AudioSink
    # ------------------------------------------------------------------

    def wants_opus(self) -> bool:
        # Recibimos PCM ya decodificado; la extensión se encarga de Opus.
        return False

    def write(self, user: Optional[discord.User], data: "voice_recv.VoiceData") -> None:
        # Defensa: si ya se llamó cleanup(), ignoramos paquetes en vuelo.
        if self._closed:
            return

        if user is None:
            return

        pcm = data.pcm
        # data.pcm es siempre bytes (b'' si vacío); ignoramos paquetes sin contenido.
        if not pcm:
            return

        # CLAVE: descartar paquetes sintéticos (PLC/FEC fill) generados por la lib
        # cuando hay huecos en la secuencia Opus. Si no, el sink puede acumular
        # cientos de MB de "silencio decodificado" durante pausas del usuario.
        if isinstance(data.packet, (FakePacket, SilencePacket)):
            self._fake_packet_counts[user.id] = self._fake_packet_counts.get(user.id, 0) + 1
            return

        if user.id not in self._buffers:
            logger.info("Comenzando a capturar audio de %s (%s).", user.display_name, user.id)
            self._buffers[user.id] = bytearray()
            self._packet_counts[user.id] = 0

        buf = self._buffers[user.id]
        # Tope de seguridad para no acumular indefinidamente.
        if len(buf) >= MAX_BUFFER_BYTES:
            return

        buf.extend(pcm)
        self._packet_counts[user.id] += 1

    def cleanup(self) -> None:
        """Llamado por la extensión al stop_listening() o cuando el sink se cierra."""
        # Marcar como cerrado ANTES de procesar para que write() ignore paquetes en vuelo
        if self._closed:
            # cleanup() se invoca de nuevo desde __del__; ignorarlo.
            return
        self._closed = True

        wav_buffers: dict[int, io.BytesIO] = {}

        # Reportar también los paquetes sintéticos que descartamos
        all_user_ids = set(self._buffers) | set(self._fake_packet_counts)
        for user_id in all_user_ids:
            pcm_data = self._buffers.get(user_id, b"")
            n_bytes = len(pcm_data)
            n_packets = self._packet_counts.get(user_id, 0)
            n_fake = self._fake_packet_counts.get(user_id, 0)
            duration_s = n_bytes / (SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH) if n_bytes else 0
            logger.info(
                "Usuario %s: %d paquetes reales (%d bytes ~%.2f s), %d paquetes sintéticos descartados.",
                user_id,
                n_packets,
                n_bytes,
                duration_s,
                n_fake,
            )

            if not pcm_data:
                continue
            wav_buffers[user_id] = _pcm_to_wav(bytes(pcm_data))

        # Liberar la memoria de los buffers; ya copiamos lo necesario a wav_buffers.
        self._buffers.clear()
        self._packet_counts.clear()
        self._fake_packet_counts.clear()

        if not wav_buffers:
            logger.warning("La grabación terminó sin audio capturado.")
            if self._callback and self._loop:
                asyncio.run_coroutine_threadsafe(self._callback({}), self._loop)
            return

        if self._callback and self._loop:
            asyncio.run_coroutine_threadsafe(self._callback(wav_buffers), self._loop)


def _pcm_to_wav(pcm_data: bytes) -> io.BytesIO:
    """Envuelve bytes PCM crudos en un contenedor WAV en memoria."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)
    buf.seek(0)
    return buf
