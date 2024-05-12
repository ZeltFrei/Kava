from typing import TYPE_CHECKING, Optional

from disnake import VoiceChannel

if TYPE_CHECKING:
    from lava.krabbe.client import Request, KavaClient


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


async def can_use_music(client: "KavaClient", user_id: int, channel_id: int) -> bool:
    """
    Check if the user can use music commands in the channel.
    :param client: The client to use.
    :param user_id: The user ID to check.
    :param channel_id: The channel ID to check.
    :return: True if the user can use music commands. False otherwise.
    """
    response = await client.request("can_use_music", user_id=user_id, channel_id=channel_id)

    if response["status"] == "error":
        return False
    elif response["status"] == "success":
        return True
    else:
        raise ValueError("Invalid response status.")
