from typing import TYPE_CHECKING

from disnake import VoiceChannel

from lava.classes.voice_client import LavalinkVoiceClient

if TYPE_CHECKING:
    from lava.krabbe.client import KavaClient, Request


async def get_client_info(client: "KavaClient", request: "Request"):
    await request.respond(
        {"bot_user_id": client.bot.user.id}
    )


async def connect(client: "KavaClient", request: "Request", channel_id: int):
    # noinspection PyTypeChecker
    channel: VoiceChannel = client.bot.get_channel(channel_id)

    if channel is None or not isinstance(channel, VoiceChannel):
        await request.respond(
            {
                "status": "error",
                "message": "Invalid channel ID."
            }
        )

        return

    if channel.guild.voice_client:
        await request.respond(
            {
                "status": "error",
                "message": "Already connected to a voice channel."
            }
        )

        return

    # noinspection PyTypeChecker
    await channel.connect(timeout=60.0, reconnect=True, cls=LavalinkVoiceClient)

    # TODO: Send a instruction message to user about how to use the bot.

    await request.respond(
        {
            "status": "success",
            "channel_id": channel.id,
            "message": "Connected to the channel."
        }
    )


def add_handlers(client: "KavaClient"):
    """
    Convenience function to add handlers from this file to the KavaClient.
    """
    client.add_handler("get_client_info", get_client_info)
    client.add_handler("connect", connect)
