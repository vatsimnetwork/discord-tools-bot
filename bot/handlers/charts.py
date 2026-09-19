import logging
from datetime import UTC, datetime, timedelta

import aiohttp
from discord import Colour, Embed, Interaction, app_commands
from discord.ext import commands

from bot.client import Bot
from bot.utils.embeds import BRAND

log = logging.getLogger(__name__)


class Charts(commands.Cog):
    AIRPORT_API = "https://api.chartfox.org/v2/airports"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._cached_airports = {}

    @app_commands.command(description="Display an airport's charts")
    @app_commands.describe(icao="Four letter airport code")
    @app_commands.guild_only()
    async def charts(self, interaction: Interaction, icao: app_commands.Range[str, 4, 4]) -> None:
        await interaction.response.defer()

        icao = icao.upper()

        if await self.has_charts_available(icao):
            embed = Embed(
                title="Charts found",
                description=f"[Click here for {icao} charts](https://chartfox.org/{icao})",
                colour=BRAND,
            )
        else:
            embed = Embed(
                title="Charts not found",
                description=f"Unfortunately we couldn't find any charts for {icao}",
                colour=Colour.red(),
            )
        embed.set_footer(text="Flight simulation use only • Powered by ChartFox")

        await interaction.followup.send(embed=embed)

    async def has_charts_available(self, icao: str) -> bool:
        cached = self._cached_airports.get(icao)
        if cached is not None and cached["last_checked"] + timedelta(minutes=15) > datetime.now(
            UTC
        ):
            return cached["has_charts"]

        headers = {"Authorization": f"Bearer {self.bot.settings.chartfox_key}"}

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(f"{self.AIRPORT_API}/{icao}") as resp:
                    # An unknown airport is a 404, which is a legitimate "no charts"
                    if resp.status == 404:
                        has_charts = False
                    elif resp.status != 200:
                        log.error("ChartFox returned %s for %s", resp.status, icao)
                        return False
                    else:
                        has_charts = bool((await resp.json()).get("has_charts"))
        except aiohttp.ClientError as error:
            log.error("Could not reach ChartFox for %s: %s", icao, error)
            return False

        self._cached_airports[icao] = {
            "has_charts": has_charts,
            "last_checked": datetime.now(UTC),
        }

        return has_charts


async def setup(bot: Bot) -> None:
    await bot.add_cog(Charts(bot))
