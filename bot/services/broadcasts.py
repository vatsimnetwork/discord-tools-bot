import json
import logging
from datetime import UTC, datetime

import discord
from aiokafka import AIOKafkaConsumer
from discord import AllowedMentions
from discord.ext import commands, tasks
from discord.utils import escape_markdown

log = logging.getLogger(__name__)

BROADCAST_TYPE = "VATSIM.Network.Dataserver.Dtos.BroadcastDto, VATSIM.Network.Dataserver"


class NetworkBroadcast:
    """Represents a network broadcast"""

    def __init__(self, timestamp, **kwargs):
        self.datetime = datetime.fromtimestamp(timestamp / 1000, UTC)
        self.callsign = kwargs.get("from", "VATSIM")
        self.message = kwargs.get("message", "No message provided")


class Broadcasts(commands.Cog):
    TOPIC = "datafeed-v1"

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self) -> None:
        # Retry rather than die on a dropped connection to the broker
        self.listener.add_exception_type(Exception)
        self.listener.start()

    async def cog_unload(self) -> None:
        self.listener.cancel()

    @tasks.loop()
    async def listener(self) -> None:
        # Connecting here rather than in before_loop, which runs outside the
        # retry handling and would kill the task if the broker is unreachable
        consumer = self._new_consumer()
        await consumer.start()

        try:
            async for message in consumer:
                if message.value.get("$type") != BROADCAST_TYPE:
                    continue

                await self.send_broadcast(NetworkBroadcast(message.timestamp, **message.value))
        finally:
            await consumer.stop()

    @listener.error
    async def listener_error(self, error: Exception) -> None:
        log.error("Kafka listener failed, restarting", exc_info=error)
        self.listener.restart()

    async def send_broadcast(self, broadcast: NetworkBroadcast) -> None:
        channel = self._broadcasts_channel()
        if channel is None:
            return

        bot_perms = channel.permissions_for(channel.guild.me)
        if not bot_perms.send_messages:
            return

        timestamp = broadcast.datetime.strftime("%H:%M:%S")
        callsign = escape_markdown(broadcast.callsign)
        body = escape_markdown(broadcast.message)

        try:
            message = await channel.send(
                content=f"**[{timestamp}] {callsign}**: {body}",
                allowed_mentions=AllowedMentions(everyone=False, users=False, roles=False),
            )

            if channel.is_news():
                await message.publish()
        except discord.DiscordException as error:
            log.warning("Error publishing network broadcast: %s", error)

    def _new_consumer(self) -> AIOKafkaConsumer:
        settings = self.bot.settings

        return AIOKafkaConsumer(
            self.TOPIC,
            security_protocol="SASL_PLAINTEXT",
            sasl_mechanism="PLAIN",
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            bootstrap_servers=settings.network_kafka_server,
            sasl_plain_username=settings.network_kafka_username,
            sasl_plain_password=settings.network_kafka_password,
            group_id=settings.network_kafka_group,
        )

    def _broadcasts_channel(self):
        channel_id = self.bot.settings.network_broadcasts_channel_id
        if channel_id is None:
            return None

        return self.bot.get_channel(channel_id)


async def setup(bot):
    await bot.add_cog(Broadcasts(bot))
