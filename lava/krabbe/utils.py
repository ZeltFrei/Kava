from typing import TYPE_CHECKING, Optional

from disnake import VoiceChannel

if TYPE_CHECKING:
    from lava.krabbe.client import Request


async def ensure_channel(request: "Request", channel_id: int) -> Optional[VoiceChannel]:
    """
    Ensure that the channel ID is valid.
    :param request: The request to respond to.
    :param channel_id: The channel ID to check.
    :return: The channel if it is valid. None otherwise.
    """
    channel = request.client.bot.get_channel(channel_id)

    if channel is None or not isinstance(channel, VoiceChannel):
        await request.respond(
            {
                "status": "error",
                "message": "Invalid channel ID."
            }
        )

        return None

    return channel
