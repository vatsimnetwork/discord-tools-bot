import logging
from typing import Any

from discord import Intents
from discord.ext import commands

from bot.settings import Settings


class Bot(commands.Bot):
    def __init__(self, settings: Settings, **kwargs: Any):
        command_prefix = "."

        case_insensitive = kwargs.pop("case_insensitive", True)

        default_intents = Intents(guilds=True, guild_messages=True)

        intents = kwargs.pop("intents", default_intents)

        super().__init__(
            command_prefix=command_prefix,
            max_messages=None,
            case_insensitive=case_insensitive,
            intents=intents,
            help_command=None,
            **kwargs,
        )

        self.log = logging.getLogger(__name__)
        self.settings = settings
        self._extensions_to_load = [
            "bot.handlers.auto_publish",
            "bot.handlers.charts",
            "bot.handlers.error_handler",
            "bot.handlers.screenshots",
            "bot.handlers.weather",
            "bot.services.broadcasts",
            "bot.services.vatsim_events",
        ]

    async def setup_hook(self) -> None:
        for name in self._extensions_to_load:
            try:
                await self.load_extension(name)
            except Exception as error:  # noqa: BLE001 - one bad extension must not abort startup
                self.log.error("%s cannot be loaded: %s", name, error)

        synced = await self.tree.sync()
        self.log.info("Synced %d application commands.", len(synced))
