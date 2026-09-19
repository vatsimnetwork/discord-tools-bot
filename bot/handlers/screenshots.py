import logging
from datetime import UTC, datetime

from discord import ButtonStyle, Embed, Interaction, Message, TextStyle, ui
from discord.ext import commands, tasks
from discord.utils import escape_markdown

from bot.client import Bot
from bot.utils.embeds import BRAND

log = logging.getLogger(__name__)

PROMPT_CUSTOM_ID = "screenshot:post"


class ScreenshotModal(ui.Modal, title="Post a screenshot"):
    image = ui.Label(text="Screenshot", component=ui.FileUpload(max_values=1))
    caption = ui.Label(
        text="Caption",
        description="Shown above the screenshot",
        component=ui.TextInput(required=False, max_length=200, style=TextStyle.short),
    )

    def __init__(self, cog: "Screenshots") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: Interaction) -> None:
        attachment = self.image.component.values[0]

        if not attachment.height or not attachment.width:
            await interaction.response.send_message("That file is not an image.", ephemeral=True)
            return

        # Downloading the attachment blows the three second interaction deadline.
        # Deferring a modal submit is a silent ack - it shows the user nothing
        await interaction.response.defer()

        caption = self.caption.component.value
        voting = interaction.channel_id == self.cog.bot.settings.screenshot_voting_channel_id

        embed = Embed(title=escape_markdown(caption) if caption else None, colour=BRAND)
        embed.set_image(url=f"attachment://{attachment.filename}")

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

        # Sending through the channel rather than the interaction, whose followup
        # renders as a reply to the prompt and is orphaned when the prompt rotates
        message = await interaction.channel.send(
            embed=embed,
            file=await attachment.to_file(),
        )

        if voting:
            await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        await self.cog.refresh_prompt(interaction.channel)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        log.error("Screenshot submission failed", exc_info=error)

        message = "Something went wrong posting that screenshot."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class ScreenshotPrompt(ui.View):
    def __init__(self, cog: "Screenshots") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @ui.button(
        label="Post a screenshot",
        style=ButtonStyle.primary,
        custom_id=PROMPT_CUSTOM_ID,
    )
    async def post(self, interaction: Interaction, button: ui.Button) -> None:
        await interaction.response.send_modal(ScreenshotModal(self.cog))


class Screenshots(commands.Cog):
    PROMPT_TEXT = "Use the button below to post a screenshot."

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._prompts: dict[int, Message] = {}

    async def cog_load(self) -> None:
        self.bot.add_view(ScreenshotPrompt(self))
        self.place_prompts.start()

    async def cog_unload(self) -> None:
        self.place_prompts.cancel()

    @tasks.loop(count=1)
    async def place_prompts(self) -> None:
        # Waiting here rather than in before_loop, which runs outside the retry handling
        await self.bot.wait_until_ready()

        for channel_id in self.bot.settings.screenshot_channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                log.warning("Screenshot channel %s not found", channel_id)
                continue

            await self._clear_stale_prompts(channel)
            await self._send_prompt(channel)

    @place_prompts.error
    async def place_prompts_error(self, error: Exception) -> None:
        log.error("Placing screenshot prompts failed, restarting", exc_info=error)
        self.place_prompts.restart()

    async def refresh_prompt(self, channel) -> None:
        """Keeps the prompt at the bottom, since only the bot can post in these channels"""
        if channel is None or channel.id not in self._prompts:
            return

        await self._prompts.pop(channel.id).delete()
        await self._send_prompt(channel)

    async def _send_prompt(self, channel) -> None:
        self._prompts[channel.id] = await channel.send(
            self.PROMPT_TEXT,
            view=ScreenshotPrompt(self),
        )

    async def _clear_stale_prompts(self, channel) -> None:
        """Drops prompts left behind by a previous run, so only one survives a restart"""
        async for message in channel.history(limit=50):
            if message.author.id != self.bot.user.id:
                continue

            if any(
                component.custom_id == PROMPT_CUSTOM_ID
                for row in message.components
                for component in getattr(row, "children", ())
            ):
                await message.delete()


async def setup(bot: Bot) -> None:
    await bot.add_cog(Screenshots(bot))
