"""
Cog de voz para el bot de Discord (discord.py con app_commands).

Slash commands:
  /join    — el bot se une al canal de voz del autor.
  /leave   — el bot abandona el canal de voz.
  /ask     — graba N segundos, transcribe y consulta el LLM (responde por texto).
  /start   — el bot empieza a escuchar de forma continua hasta /stop.
  /stop    — detiene la grabación y ejecuta el pipeline completo:
             STT → LLM (prompt voz) → TTS → reproduce el audio en el canal.
"""

import asyncio
import io
import logging

import discord
from discord import app_commands
from discord.ext import commands, voice_recv

from src import asr, audio, llm, tts
from src.llm import strip_markdown
from src.sink import WaveSink

logger = logging.getLogger(__name__)

DEFAULT_RECORD_SECONDS = 10
MAX_RECORD_SECONDS = 60


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Sink activo por guild para el modo /start … /stop
        self._continuous_sinks: dict[int, WaveSink] = {}
        # Futures donde el callback del sink deposita los buffers WAV
        self._sink_futures: dict[int, asyncio.Future[dict[int, io.BytesIO]]] = {}

    # ------------------------------------------------------------------
    # /join
    # ------------------------------------------------------------------

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
            await interaction.response.send_message(
                f"Me moví a **{channel.name}**.", ephemeral=True
            )
        else:
            await channel.connect(cls=voice_recv.VoiceRecvClient)
            await interaction.response.send_message(
                f"Me uní a **{channel.name}**.", ephemeral=True
            )

    # ------------------------------------------------------------------
    # /leave
    # ------------------------------------------------------------------

    @app_commands.command(name="leave", description="El bot abandona el canal de voz.")
    async def leave(self, interaction: discord.Interaction) -> None:
        if not interaction.guild.voice_client:
            await interaction.response.send_message(
                "No estoy en ningún canal de voz.", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        self._continuous_sinks.pop(guild_id, None)
        self._sink_futures.pop(guild_id, None)

        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Me desconecté del canal de voz.", ephemeral=True)

    # ------------------------------------------------------------------
    # /ask  — grabación cronometrada → texto
    # ------------------------------------------------------------------

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
            await interaction.response.send_message(
                "Debes estar en un canal de voz. Usa `/join` primero.", ephemeral=True
            )
            return

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
            all_texts: list[str] = []
            for user_id, wav_buf in wav_buffers.items():
                try:
                    text = await asr.transcribe(wav_buf)
                    if text:
                        member = interaction.guild.get_member(user_id)
                        name = member.display_name if member else str(user_id)
                        logger.info("[ASR] %s: %s", name, text)
                        all_texts.append(text)
                except Exception as exc:
                    logger.error("Error transcribiendo audio del usuario %s: %s", user_id, exc)

            transcription_result["text"] = " ".join(all_texts)
            recording_done.set()

        sink.set_callback(on_recording_finished, asyncio.get_event_loop())

        status_msg = await interaction.followup.send(
            f"Grabando durante **{segundos}** segundo(s)... Habla ahora."
        )

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
            await status_msg.edit(
                content="No se detectó voz en la grabación. Intenta hablar más cerca del micrófono."
            )
            return

        await status_msg.edit(content=f"Transcripción: *{transcript}*\n\nPensando...")

        try:
            answer = await llm.ask(transcript)
        except ConnectionError as exc:
            await status_msg.edit(content=f"Error de conexión con Ollama: {exc}")
            return
        except Exception as exc:
            logger.error("Error en LLM: %s", exc)
            await status_msg.edit(
                content="Ocurrió un error al consultar el modelo de lenguaje."
            )
            return

        embed = discord.Embed(color=discord.Color.blurple())
        embed.add_field(name="Pregunta (transcripción)", value=transcript[:1024], inline=False)
        embed.add_field(name="Respuesta", value=answer[:1024], inline=False)
        embed.set_footer(text=f"Modelo: {llm.config.OLLAMA_MODEL}")
        await status_msg.edit(content=None, embed=embed)

    # ------------------------------------------------------------------
    # /start  — inicia grabación continua hasta /stop
    # ------------------------------------------------------------------

    @app_commands.command(
        name="start",
        description="El bot empieza a escucharte. Usa /stop cuando termines para obtener respuesta por voz.",
    )
    async def start(self, interaction: discord.Interaction) -> None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "Debes estar en un canal de voz. Usa `/join` primero.", ephemeral=True
            )
            return

        if interaction.guild.id in self._continuous_sinks:
            await interaction.response.send_message(
                "Ya estoy escuchando. Usa `/stop` para obtener la respuesta.", ephemeral=True
            )
            return

        vc: voice_recv.VoiceRecvClient | None = interaction.guild.voice_client  # type: ignore[assignment]
        if not vc:
            vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        elif not isinstance(vc, voice_recv.VoiceRecvClient):
            await vc.disconnect(force=True)
            vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient)

        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict[int, io.BytesIO]] = loop.create_future()
        self._sink_futures[interaction.guild.id] = future

        sink = WaveSink()

        async def _on_buffers(wav_buffers: dict[int, io.BytesIO]) -> None:
            if not future.done():
                future.set_result(wav_buffers)

        sink.set_callback(_on_buffers, loop)
        self._continuous_sinks[interaction.guild.id] = sink

        vc.listen(sink)
        logger.info("Grabación continua iniciada en guild %s.", interaction.guild.id)
        await interaction.response.send_message(
            "Escuchando... Habla cuando quieras. Usa `/stop` cuando termines para que te responda por voz."
        )

    # ------------------------------------------------------------------
    # /stop  — detiene grabación y ejecuta pipeline STT → LLM → TTS → audio
    # ------------------------------------------------------------------

    @app_commands.command(
        name="stop",
        description="Detiene la escucha, procesa tu pregunta y responde con voz.",
    )
    async def stop(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id
        sink = self._continuous_sinks.pop(guild_id, None)
        future = self._sink_futures.pop(guild_id, None)

        if not sink or not future:
            await interaction.response.send_message(
                "No estoy escuchando ahora mismo. Usa `/start` primero.", ephemeral=True
            )
            return

        vc: voice_recv.VoiceRecvClient | None = interaction.guild.voice_client  # type: ignore[assignment]

        # Diferir ANTES de stop_listening para cubrir la latencia STT+LLM+TTS
        await interaction.response.defer()

        if vc and isinstance(vc, voice_recv.VoiceRecvClient):
            vc.stop_listening()

        logger.info("Grabación continua detenida en guild %s. Procesando...", guild_id)
        status_msg = await interaction.followup.send("Procesando tu pregunta...")

        # Esperar a que el callback del sink deposite los buffers
        try:
            wav_buffers = await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            await status_msg.edit(content="No se recibieron datos de audio. ¿Estabas hablando?")
            return

        # --- STT ---
        await status_msg.edit(content="Transcribiendo audio...")
        transcript = await self._transcribe_all(wav_buffers, interaction.guild)

        if not transcript:
            await status_msg.edit(
                content="No se detectó voz en la grabación. Habla más cerca del micrófono."
            )
            return

        # --- LLM ---
        await status_msg.edit(content=f"Escuché: *{transcript[:200]}*\n\nGenerando respuesta...")
        try:
            answer = await llm.ask(transcript, system=llm.VOICE_SYSTEM_PROMPT)
        except ConnectionError as exc:
            await status_msg.edit(content=f"Error de conexión con Ollama: {exc}")
            return
        except Exception as exc:
            logger.error("Error en LLM: %s", exc)
            await status_msg.edit(content="Error al consultar el modelo de lenguaje.")
            return

        # --- TTS ---
        clean_answer = strip_markdown(answer)
        await status_msg.edit(content="Sintetizando voz...")
        try:
            wav_path = await tts.synthesize(clean_answer)
        except Exception as exc:
            logger.error("Error en TTS: %s", exc)
            await status_msg.edit(
                content=f"Error al generar audio. Respuesta en texto:\n\n{answer[:1500]}"
            )
            return

        # --- Reproducción ---
        if not vc or not vc.is_connected():
            await status_msg.edit(
                content=f"Me desconecté antes de reproducir. Respuesta:\n\n{answer[:1500]}"
            )
            return

        await status_msg.edit(content="Reproduciendo respuesta...")
        try:
            await audio.play_wav(vc, wav_path)
        except Exception as exc:
            logger.error("Error reproduciendo audio: %s", exc)
            await status_msg.edit(
                content=f"Error al reproducir. Respuesta:\n\n{answer[:1500]}"
            )
            return

        # --- Resumen final en texto ---
        embed = discord.Embed(color=discord.Color.green())
        embed.add_field(name="Tu pregunta", value=transcript[:1024], inline=False)
        embed.add_field(name="Respuesta", value=answer[:1024], inline=False)
        embed.set_footer(text=f"Modelo: {llm.config.OLLAMA_MODEL}")
        await status_msg.edit(content=None, embed=embed)

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    async def _transcribe_all(
        self, wav_buffers: dict[int, io.BytesIO], guild: discord.Guild
    ) -> str:
        """Transcribe todos los buffers de usuario y concatena el resultado."""
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
