import asyncio
import logging
from datetime import UTC, datetime, timedelta
from enum import Enum, unique

import aiohttp
from discord import Colour, Embed
from discord.ext import commands, tasks

from bot.client import Bot

log = logging.getLogger(__name__)

POSTING_LEAD = timedelta(hours=1, minutes=45)


@unique
class EventType(Enum):
    NORMAL = "Event"
    VSO = "VASOPS Event"
    CPT = "Controller Examination"


class Event:
    EVENTS_API = "https://my.vatsim.net/api/v2/events/latest"

    def __init__(self, *, type, name, link, start_time, short_description, banner, **kwargs):
        self.type = EventType(type)
        self.name = name
        self.link = link
        self.start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
        self.short_description = short_description.strip()
        self.banner_url = banner

    @classmethod
    async def get_current_postings(cls) -> list:
        for attempt in range(1, 4):  # Max 3 attempts
            async with aiohttp.ClientSession() as session:
                async with session.get(cls.EVENTS_API) as resp:
                    if resp.status == 200:
                        events = await resp.json()
                        return list(
                            filter(
                                lambda event: event.should_be_posted_now(),
                                [cls(**event) for event in events["data"]],
                            )
                        )
            await asyncio.sleep(2**attempt)
        return []  # Failed all attempts

    @property
    def embed(self):
        embed = Embed(
            title=self.name,
            description=self.short_description,
            url=self.link,
            timestamp=self.start_time,
            colour=Colour.from_rgb(43, 57, 144),
        )

        embed.set_image(url=self.banner_url)
        if self.type == EventType.CPT:
            embed.set_footer(text="Best of luck! Starting time \N{BLACK RIGHTWARDS ARROW}")
        else:
            embed.set_footer(text="Starting time \N{BLACK RIGHTWARDS ARROW}")

        return embed

    def is_about_to_start(self) -> bool:
        return self.start_time - POSTING_LEAD <= datetime.now(UTC)

    def has_expired(self) -> bool:
        return self.start_time < datetime.now(UTC)

    def should_be_posted_now(self) -> bool:
        return self.is_about_to_start() and not self.has_expired()


class EventPoster(commands.Cog):
    # Covers the whole window an event is postable in, plus a loop interval of slack
    HISTORY_WINDOW = POSTING_LEAD + timedelta(minutes=30)

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.automated_postings.start()

    async def cog_unload(self) -> None:
        self.automated_postings.cancel()

    @tasks.loop(minutes=15)
    async def automated_postings(self) -> None:
        events = await Event.get_current_postings()
        if not events:
            return

        already_posted = {}

        for event in events:
            if not event.link:
                log.warning("Skipping %s: no link to deduplicate on", event.name)
                continue

            channel = self._channel_for(event)
            if channel is None:
                continue

            if channel.id not in already_posted:
                already_posted[channel.id] = await self._recently_posted(channel)

            if event.link in already_posted[channel.id]:
                continue

            message = await channel.send(embed=event.embed)
            already_posted[channel.id].add(event.link)

            if channel.is_news():
                await message.publish()

    @automated_postings.error
    async def automated_postings_error(self, error: Exception) -> None:
        log.error("Event posting failed, restarting loop", exc_info=error)
        self.automated_postings.restart()

    def _channel_for(self, event: Event):
        settings = self.bot.settings
        channel_id = (
            settings.exams_channel_id if event.type == EventType.CPT else settings.events_channel_id
        )
        if channel_id is None:
            return None

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return None

        permissions = channel.permissions_for(channel.guild.me)
        # Without history the dedupe scan comes back empty and every tick reposts
        if not (
            permissions.send_messages
            and permissions.embed_links
            and permissions.read_message_history
        ):
            log.warning("Missing permissions to post events in %s", channel_id)
            return None

        return channel

    async def _recently_posted(self, channel) -> set[str]:
        """Event links already announced in the channel, standing in for a dedupe table"""
        links = set()

        after = datetime.now(UTC) - self.HISTORY_WINDOW
        async for message in channel.history(after=after, limit=None):
            if message.author.id != self.bot.user.id:
                continue

            links.update(embed.url for embed in message.embeds if embed.url)

        return links


async def setup(bot: Bot) -> None:
    await bot.add_cog(EventPoster(bot))
