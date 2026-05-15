"""
Voice cog for Discord Helper.

Sprint 5:
- per-guild state container
- per-guild conversation history
- /clear command
- sanitize_for_tts before voice playback
"""

import asyncio
import io
import logging
import os
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands, voice_recv

from src import asr, audio, llm, tts
from src.sink import WaveSink
from src.text_utils import sanitize_for_tts

logger = logging.getLogger(__name__)

DEFAULT_RECORD_SECONDS = 10
MAX_RECORD_SECONDS = 60


@dataclass
class GuildVoiceState:
    """Per-guild mutable voice state.

    The cog is a singleton, so all mutable state must be stored behind guild_id
    to avoid one server affecting another.
    """

    recording: bool = False
    active_sink: WaveSink | None = None
    future: asyncio.Future[dict[int, io.BytesIO]] | None = None
    history: list[dict] = field(default_factory=list)


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._guild_state: dict[int, GuildVoiceState] = {}

    def _state(self, guild_id: int) -> GuildVoiceState:
        if guild_id not in self._guild_state:
            self._guild_state[guild_id] = GuildVoiceState()
        return self._guild_state[guild_id]

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after) -> None:
        if member.id != self.bot.user.id:
            return

        if before.channel and after.channel is None and before.guild:
            self._guild_state.pop(before.guild.id, None)
            logger.info("Voice state cleaned for guild %s", before.guild.id)

    @app_commands.command(name="join", description="El bot se une a tu canal de voz.")
    async def join(self, interaction: discord.Interaction) -> None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "Debes estar en un canal de voz para usar este comando.", ephemeral=True
            )
            return

        channel = interaction.user.voice.channel

        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
            await interaction.response.send_message(f"Me moví a **{channel.name}**.", ephemeral=True)
        else:
            await channel.connect(cls=voice_recv.VoiceRecvClient)
            await interaction.response.send_message(f"Me uní a **{channel.name}**.", ephemeral=True)

    @app_commands.command(name="leave", description="El bot abandona el canal de voz.")
    async def leave(self, interaction: discord.Interaction) -> None:
        if not interaction.guild.voice_client:
            await interaction.response.send_message("No estoy en ningún canal de voz.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        self._guild_state.pop(guild_id, None)

        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Me desconecté del canal de voz.", ephemeral=True)

    @app_commands.command(name="clear", description="Limpia el historial conversacional de este servidor.")
    async def clear(self, interaction: discord.Interaction) -> None:
        state = self._state(interaction.guild.id)
        state.history.clear()
        await interaction.response.send_message("Historial conversacional limpiado.", ephemeral=True)

    @app_commands.command(
        name="ask",
        description="Graba tu voz, la transcribe y consulta el LLM local (responde en texto).",
    )
    @app_commands.describe(
        segundos=f"Duración de la grabación en segundos (1-{MAX_RECORD_SECONDS}, por defecto {DEFAULT_RECORD_SECONDS})."
    )
    async def ask(
        self,
        interaction: discord.Interaction,
        segundos: app_commands.Range[int, 1, MAX_RECORD_SECONDS] = DEFAULT_RECORD_SECONDS,
    ) -> None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Debes estar en un canal de voz. Usa `/join` primero.", ephemeral=True)
            return

        state = self._state(interaction.guild.id)
        vc: voice_recv.VoiceRecvClient | None = interaction.guild.voice_client  # type: ignore[assignment]

        if not vc:
            vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        elif not isinstance(vc, voice_recv.VoiceRecvClient):
            await vc.disconnect(force=True)
            vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient)

        await interaction.response.defer()

        sink = WaveSink()
        transcription_result: dict[str, str] = {}
        recording_done = asyncio.Event()

        async def on_recording_finished(wav_buffers: dict[int, io.BytesIO]) -> None:
            transcription_result["text"] = await self._transcribe_all(wav_buffers, interaction.guild)
            recording_done.set()

        sink.set_callback(on_recording_finished, asyncio.get_event_loop())

        status_msg = await interaction.followup.send(f"Grabando durante **{segundos}** segundo(s)... Habla ahora.")

        vc.listen(sink)
        await asyncio.sleep(segundos)
        vc.stop_listening()

        await status_msg.edit(content="Transcribiendo audio...")
        try:
            await asyncio.wait_for(recording_done.wait(), timeout=120)
        except asyncio.TimeoutError:
            await status_msg.edit(content="La transcripción tardó demasiado. Intenta de nuevo.")
            return

        transcript = transcription_result.get("text", "").strip()

        if not transcript:
            await status_msg.edit(content="No se detectó voz en la grabación. Intenta hablar más cerca del micrófono.")
            return

        await status_msg.edit(content=f"Transcripción: *{transcript}*\n\nPensando...")

        try:
            answer = await llm.ask(transcript, history=state.history)
        except ConnectionError as exc:
            await status_msg.edit(content=f"Error de conexión con Ollama: {exc}")
            return
        except Exception as exc:
            logger.error("Error en LLM: %s", exc)
            await status_msg.edit(content="Ocurrió un error al consultar el modelo de lenguaje.")
            return

        self._append_history(state, transcript, answer)

        embed = discord.Embed(color=discord.Color.blurple())
        embed.add_field(name="Pregunta (transcripción)", value=transcript[:1024], inline=False)
        embed.add_field(name="Respuesta", value=answer[:1024], inline=False)
        embed.set_footer(text=f"Modelo: {llm.config.OLLAMA_MODEL}")
        await status_msg.edit(content=None, embed=embed)

    @app_commands.command(
        name="start",
        description="El bot empieza a escucharte. Usa /stop cuando termines para obtener respuesta por voz.",
    )
    async def start(self, interaction: discord.Interaction) -> None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Debes estar en un canal de voz. Usa `/join` primero.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        state = self._state(guild_id)

        if state.recording:
            await interaction.response.send_message("Ya estoy escuchando. Usa `/stop` para obtener la respuesta.", ephemeral=True)
            return

        vc: voice_recv.VoiceRecvClient | None = interaction.guild.voice_client  # type: ignore[assignment]

        if not vc:
            vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        elif not isinstance(vc, voice_recv.VoiceRecvClient):
            await vc.disconnect(force=True)
            vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient)

        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict[int, io.BytesIO]] = loop.create_future()
        sink = WaveSink()

        async def _on_buffers(wav_buffers: dict[int, io.BytesIO]) -> None:
            if not future.done():
                future.set_result(wav_buffers)

        sink.set_callback(_on_buffers, loop)

        state.recording = True
        state.active_sink = sink
        state.future = future

        vc.listen(sink)
        logger.info("Grabación continua iniciada en guild %s.", guild_id)
        await interaction.response.send_message("Escuchando... Habla cuando quieras. Usa `/stop` cuando termines para que te responda por voz.")

    @app_commands.command(name="stop", description="Detiene la escucha, procesa tu pregunta y responde con voz.")
    async def stop(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id
        state = self._state(guild_id)

        if not state.recording or not state.active_sink or not state.future:
            await interaction.response.send_message("No estoy escuchando ahora mismo. Usa `/start` primero.", ephemeral=True)
            return

        vc: voice_recv.VoiceRecvClient | None = interaction.guild.voice_client  # type: ignore[assignment]
        future = state.future

        await interaction.response.defer()

        if vc and isinstance(vc, voice_recv.VoiceRecvClient):
            vc.stop_listening()

        state.recording = False
        state.active_sink = None
        state.future = None

        status_msg = await interaction.followup.send("Procesando tu pregunta...")

        try:
            wav_buffers = await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            await status_msg.edit(content="No se recibieron datos de audio. ¿Estabas hablando?")
            return

        await status_msg.edit(content="Transcribiendo audio...")
        transcript = await self._transcribe_all(wav_buffers, interaction.guild)

        if not transcript:
            await status_msg.edit(content="No se detectó voz en la grabación. Habla más cerca del micrófono.")
            return

        await status_msg.edit(content=f"Escuché: *{transcript[:200]}*\n\nGenerando respuesta...")

        try:
            answer = await llm.ask(transcript, history=state.history, system=llm.VOICE_SYSTEM_PROMPT)
        except ConnectionError as exc:
            await status_msg.edit(content=f"Error de conexión con Ollama: {exc}")
            return
        except Exception as exc:
            logger.error("Error en LLM: %s", exc)
            await status_msg.edit(content="Error al consultar el modelo de lenguaje.")
            return

        self._append_history(state, transcript, answer)

        clean_answer = sanitize_for_tts(answer)
        await status_msg.edit(content="Sintetizando voz...")

        wav_path: str | None = None
        try:
            wav_path = await tts.synthesize(clean_answer)

            if not vc or not vc.is_connected():
                await status_msg.edit(content=f"Me desconecté antes de reproducir. Respuesta:\n\n{answer[:1500]}")
                return

            await status_msg.edit(content="Reproduciendo respuesta...")
            await audio.play_wav(vc, wav_path)

        except Exception as exc:
            logger.error("Error en pipeline TTS/audio: %s", exc)
            await status_msg.edit(content=f"Error al reproducir audio. Respuesta en texto:\n\n{answer[:1500]}")
            return
        finally:
            if wav_path and os.path.exists(wav_path):
                os.unlink(wav_path)

        embed = discord.Embed(color=discord.Color.green())
        embed.add_field(name="Tu pregunta", value=transcript[:1024], inline=False)
        embed.add_field(name="Respuesta", value=answer[:1024], inline=False)
        embed.set_footer(text=f"Modelo: {llm.config.OLLAMA_MODEL}")
        await status_msg.edit(content=None, embed=embed)

    def _append_history(self, state: GuildVoiceState, user_text: str, assistant_text: str) -> None:
        state.history.append({"role": "user", "content": user_text})
        state.history.append({"role": "assistant", "content": assistant_text})
        state.history = llm.trim_history(state.history)

    async def _transcribe_all(self, wav_buffers: dict[int, io.BytesIO], guild: discord.Guild) -> str:
        all_texts: list[str] = []

        for user_id, wav_buf in wav_buffers.items():
            try:
                text = await asr.transcribe(wav_buf)
                if text:
                    member = guild.get_member(user_id)
                    name = member.display_name if member else str(user_id)
                    logger.info("[ASR] %s: %s", name, text)
                    all_texts.append(text)
            except Exception as exc:
                logger.error("Error transcribiendo audio del usuario %s: %s", user_id, exc)

        return " ".join(all_texts).strip()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceCog(bot))
