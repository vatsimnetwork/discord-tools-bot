from datetime import UTC, datetime

from discord import Attachment, Embed, Interaction, app_commands
from discord.ext import commands
from discord.utils import escape_markdown

from bot.client import Bot
from bot.utils.embeds import BRAND


class Screenshots(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @app_commands.command(description="Post a screenshot")
    @app_commands.describe(image="The screenshot to post", caption="Shown above the screenshot")
    @app_commands.guild_only()
    async def screenshot(
        self,
        interaction: Interaction,
        image: Attachment,
        caption: app_commands.Range[str, 1, 200] | None = None,
    ) -> None:
        if not image.height or not image.width:
            await interaction.response.send_message(
                "That file is not an image.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        voting = interaction.channel_id == self.bot.settings.screenshot_voting_channel_id

        embed = Embed(
            title=escape_markdown(caption) if caption else None,
            colour=BRAND,
        )

        embed.set_image(url=f"attachment://{image.filename}")

        if voting:
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url,
            )

            embed.set_footer(text="Like this screenshot? React below!")
        else:
            embed.timestamp = datetime.now(UTC)

            embed.set_footer(
                text=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url,
            )

        message = await interaction.followup.send(
            embed=embed,
            file=await image.to_file(),
            wait=True,
        )

        if voting:
            await message.add_reaction("✅")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Screenshots(bot))
