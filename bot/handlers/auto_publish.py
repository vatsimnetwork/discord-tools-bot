import logging

import discord
from discord import ChannelType, Message
from discord.ext import commands

from bot.client import Bot

log = logging.getLogger(__name__)


class AutoPublish(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.channel.type is not ChannelType.news:
            return

        # The bot publishes its own posts as it sends them. System messages and
        # ones relayed from a followed channel cannot be published
        if (
            message.author.id == self.bot.user.id
            or message.is_system()
            or message.flags.is_crossposted
        ):
            return

        # Publishing another member's message takes Manage Messages; withholding it opts a channel out
        if not message.channel.permissions_for(message.guild.me).manage_messages:
            return

        try:
            await message.publish()
        except discord.HTTPException as error:
            log.warning("Error publishing message %s: %s", message.id, error)


async def setup(bot: Bot) -> None:
    await bot.add_cog(AutoPublish(bot))
