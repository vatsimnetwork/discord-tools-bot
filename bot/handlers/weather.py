from datetime import UTC, datetime, timedelta

import aiohttp
import discord
from discord import Colour, Interaction, app_commands
from discord.ext import commands

from bot.client import Bot
from bot.utils.embeds import BRAND


class Weather(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._cached_metars = {}

    @app_commands.command(description="Display an airport's weather reports")
    @app_commands.describe(icao="Four letter airport code")
    @app_commands.guild_only()
    async def metar(self, interaction: Interaction, icao: app_commands.Range[str, 4, 4]) -> None:
        await interaction.response.defer()

        icao = icao.upper()

        reports = await self.fetch_reports(icao)

        embed = self.fetch_embed(interaction, icao, **reports)

        await interaction.followup.send(embed=embed)

    async def fetch_reports(self, icao: str):
        latest_data = self._cached_metars.get(icao, None)

        # Cache responses for 15 minutes
        if latest_data is None or latest_data["last_checked"] + timedelta(
            minutes=15
        ) <= datetime.now(UTC):
            self._cached_metars[icao] = {
                "vatsim_metar": await self._fetch_vatsim_metar(icao),
                "avwx_taf": await self._fetch_avwx_taf(icao),
                "last_checked": datetime.now(UTC),
            }

        return self._cached_metars[icao]

    def fetch_embed(
        self,
        interaction: Interaction,
        icao: str,
        *,
        vatsim_metar: str | None = None,
        avwx_taf: str | None = None,
        **kwargs,
    ):
        if vatsim_metar is None and avwx_taf is None:
            embed = discord.Embed(
                title=f"No weather reports found for {icao}",
                description="Please make sure you've requested a valid airport code",
                color=Colour.red(),
            )
        else:
            embed = discord.Embed(title=f"{icao} - Weather Report", color=BRAND)
            if vatsim_metar is not None:
                embed.add_field(name="METAR (VATSIM)", value=vatsim_metar, inline=False)
            if avwx_taf is not None:
                embed.add_field(name="TAF (AVWX)", value=avwx_taf, inline=False)

        last_checked = kwargs.get("last_checked", datetime.now(UTC))
        embed.set_footer(text=f"Requested by {interaction.user}")
        embed.timestamp = last_checked

        return embed

    async def _fetch_vatsim_metar(self, icao: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://metar.vatsim.net/{icao}") as resp:
                if resp.status != 200:
                    return None
                else:
                    text = (await resp.text()).strip()
                    return text if text != "" else None

    async def _fetch_avwx_taf(self, icao: str) -> str:
        async with (
            aiohttp.ClientSession(
                headers={"Authorization": f"Token {self.bot.settings.avwx_key}"}
            ) as session,
            session.get(f"https://avwx.rest/api/taf/{icao}") as resp,
        ):
            if resp.status != 200:
                return None

            data = await resp.json()
            if "forecast" not in data or len(data["forecast"]) == 0:
                return None

            taf = f"TAF {icao} "
            if data["time"] is not None:
                taf += f"{data['time']['repr']} "

            taf += f"{data['forecast'][0]['sanitized']}"

            for forecast in data["forecast"][1:]:
                taf += f"\n{forecast['sanitized']}"

            return taf


async def setup(bot: Bot) -> None:
    await bot.add_cog(Weather(bot))
