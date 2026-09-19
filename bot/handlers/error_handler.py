import logging

from discord import Interaction, app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._previous_handler = bot.tree.on_error

    async def cog_load(self):
        self.bot.tree.on_error = self.on_app_command_error

    async def cog_unload(self):
        self.bot.tree.on_error = self._previous_handler

    async def on_app_command_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ) -> None:
        error = getattr(error, "original", error)
        log.error("Exception in command %s", interaction.command, exc_info=error)

        message = "Something went wrong running that command."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CommandErrorHandler(bot))
