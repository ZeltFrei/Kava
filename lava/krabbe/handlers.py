from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lava.krabbe.client import KavaClient, Request


async def on_get_user_id(client: "KavaClient", request: "Request"):
    await request.respond(
        {"bot_user_id": client.bot.user.id}
    )


def add_handlers(client: "KavaClient"):
    """
    Convenience function to add handlers from this file to the KavaClient.
    """
    client.add_handler("bot_user_id", on_get_user_id)
