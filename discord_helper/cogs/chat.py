"""
Cog de chat de texto para el bot (discord.py con app_commands).

Dos formas de interactuar con el LLM:
  1. Slash command /chat <mensaje>
  2. Mención directa: @AmlaBot <mensaje>
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from discord_helper.core import llm

logger = logging.getLogger(__name__)

MAX_FIELD_LENGTH = 1024
MAX_RESPONSE_LENGTH = 1900


class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="chat", description="Envía un mensaje de texto al asistente IA local.")
    @app_commands.describe(mensaje="Escribe tu pregunta o mensaje aquí.")
    async def chat(self, interaction: discord.Interaction, mensaje: str) -> None:
        await interaction.response.defer()

        try:
            respuesta = await llm.ask(mensaje)
        except ConnectionError as exc:
            await interaction.followup.send(
                f"Error de conexión con Ollama: {exc}", ephemeral=True
            )
            return
        except Exception as exc:
            logger.error("Error en LLM (/chat): %s", exc)
            await interaction.followup.send(
                "Ocurrió un error al consultar el modelo. Revisa que Ollama esté corriendo.",
                ephemeral=True,
            )
            return

        embed = _build_embed(mensaje, respuesta)
        await interaction.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if self.bot.user not in message.mentions:
            return

        contenido = message.content
        for mention in [f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"]:
            contenido = contenido.replace(mention, "")
        contenido = contenido.strip()

        if not contenido:
            await message.reply(
                "Hola! Puedes preguntarme algo escribiendo `@AmlaBot <tu pregunta>` "
                "o usando el comando `/chat`."
            )
            return

        async with message.channel.typing():
            try:
                respuesta = await llm.ask(contenido)
            except ConnectionError as exc:
                await message.reply(f"Error de conexión con Ollama: {exc}")
                return
            except Exception as exc:
                logger.error("Error en LLM (mención): %s", exc)
                await message.reply(
                    "Ocurrió un error al consultar el modelo. Revisa que Ollama esté corriendo."
                )
                return

        embed = _build_embed(contenido, respuesta)
        await message.reply(embed=embed)


def _build_embed(pregunta: str, respuesta: str) -> discord.Embed:
    embed = discord.Embed(color=discord.Color.blurple())
    embed.add_field(name="Pregunta", value=pregunta[:MAX_FIELD_LENGTH], inline=False)
    respuesta_display = respuesta[:MAX_RESPONSE_LENGTH]
    if len(respuesta) > MAX_RESPONSE_LENGTH:
        respuesta_display += "\n*(respuesta truncada)*"
    embed.add_field(name="Respuesta", value=respuesta_display[:MAX_FIELD_LENGTH], inline=False)
    embed.set_footer(text=f"Modelo: {llm.config.OLLAMA_MODEL}")
    return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChatCog(bot))
