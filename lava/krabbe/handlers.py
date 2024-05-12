import re
from typing import TYPE_CHECKING, Optional

from lavalink import LoadResult, LoadType

from lava.classes.player import LavaPlayer
from lava.classes.voice_client import LavalinkVoiceClient
from lava.embeds import InfoEmbed
from lava.krabbe.utils import ensure_channel

if TYPE_CHECKING:
    from lava.krabbe.client import KavaClient, Request


async def get_client_info(client: "KavaClient", request: "Request"):
    await request.respond(
        {"bot_user_id": client.bot.user.id}
    )


async def connect(client: "KavaClient", request: "Request", owner_id: int, channel_id: int):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    if channel.guild.voice_client:
        await request.respond(
            {
                "status": "error",
                "message": "機器人已經連接到語音頻道。"
            }
        )
        return

    # noinspection PyTypeChecker
    await channel.connect(timeout=60.0, reconnect=True, cls=LavalinkVoiceClient)

    await channel.send(
        content=f"<@{owner_id}>",
        embed=InfoEmbed(
            title="召喚成功",
            description=f"{client.bot.user.mention} 是我們為您分配的音樂機器人，請使用 斜線命令 `/` 來播放音樂。 "
        )
    )

    player = client.bot.lavalink.player_manager.get(channel.guild.id)
    player.enter_disconnect_timeout()

    await request.respond(
        {
            "status": "success",
            "channel_id": channel.id,
            "message": f"Krabbe 2.0 已為您的語音頻道分配音樂機器人，請查看您的語音文字頻道 {channel.name}。"
        }
    )


async def nowplaying(client: "KavaClient", request: "Request", channel_id: int):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    if not channel.guild.voice_client:
        await request.respond(
            {
                "status": "error",
                "message": "機器人尚未連接到語音頻道。"
            }
        )
        return

    player: LavaPlayer = client.bot.lavalink.player_manager.get(channel.guild.id)

    await player.update_display(new_message=await channel.send("Loading..."))

    await request.respond(
        {
            "status": "success",
            "message": "成功顯示目前正在播放的歌曲。"
        }
    )


async def play(client: "KavaClient", request: "Request", channel_id: int, author_id: int, query: str,
               index: Optional[int]):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    player: LavaPlayer = client.bot.lavalink.player_manager.get(channel.guild.id)

    results: LoadResult = await player.node.get_tracks(query)

    # Check locals
    if not results or not results.tracks:
        client.bot.logger.info("No results found with lavalink for query %s, checking local sources", query)
        results: LoadResult = await client.bot.lavalink.get_local_tracks(query)

    if not results or not results.tracks:  # If nothing was found
        await request.respond(
            {
                "status": "error",
                "message": "找不到符合條件的歌曲。如果你想要使用關鍵字搜尋，請在輸入關鍵字後等待幾秒，搜尋結果將會自動顯示在上方。"
            }
        )
        return

    # Find the index song should be (In front of any autoplay songs)
    if not index:
        index = sum(1 for t in player.queue if t.requester)
    else:
        index -= 1

    match results.load_type:
        case LoadType.TRACK:
            player.add(
                requester=author_id,
                track=results.tracks[0], index=index
            )

            await request.respond(
                {
                    "status": "success",
                    "message": f"成功加入播放序列：{results.tracks[0].title}"
                }
            )

        case LoadType.PLAYLIST:
            # TODO: Ask user if they want to add the whole playlist or just some tracks

            for iter_index, track in enumerate(results.tracks):
                player.add(
                    requester=author_id, track=track,
                    index=index + iter_index
                )

            # noinspection PyTypeChecker
            request.respond(
                {
                    "status": "success",
                    "message": f"成功加入播放序列：{len(results.tracks)} / {results.playlist_info.name}"
                }
            ),

    # If the player isn't already playing, start it.
    if not player.is_playing:
        await player.play()

    await player.update_display(new_message=await channel.send(content="Loading..."))


async def search(client: "KavaClient", request: "Request", query: str):
    if re.match(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+", query):
        await request.respond(
            {
                "status": "success",
                "results": []
            }
        )

    if not query:
        await request.respond(
            {
                "status": "success",
                "results": []
            }
        )

    choices = []

    result = await client.bot.lavalink.get_tracks(f"ytsearch:{query}")

    for track in result.tracks:
        choices.append(
            {
                "name": f"{track.title[:80]} by {track.author[:16]}",
                "value": track.uri
            }
        )

    await request.respond(
        {
            "status": "success",
            "results": choices
        }
    )


async def skip(client: "KavaClient", request: "Request", channel_id: int, target: int, move: bool):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    player: LavaPlayer = client.bot.lavalink.player_manager.get(channel.guild.id)

    if not player.is_playing:
        await request.respond(
            {
                "status": "error",
                "message": "沒有正在播放的歌曲"
            }
        )
        return

    if target:
        if len(player.queue) < target or target < 1:
            await request.respond(
                {
                    "status": "error",
                    "message": "無效的歌曲編號"
                }
            )
            return

        if move:
            player.queue.insert(0, player.queue.pop(target - 1))

        else:
            player.queue = player.queue[target - 1:]

    await player.skip()

    await request.respond(
        {
            "status": "success",
            "message": "成功跳過歌曲"
        }
    )

    await player.update_display(new_message=await channel.send("Loading..."))


async def remove(client: "KavaClient", request: "Request", channel_id: int, target: int):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    player: LavaPlayer = client.bot.lavalink.player_manager.get(channel.guild.id)

    if not player.is_playing:
        await request.respond(
            {
                "status": "error",
                "message": "沒有正在播放的歌曲"
            }
        )
        return

    if len(player.queue) < target or target < 1:
        await request.respond(
            {
                "status": "error",
                "message": "無效的歌曲編號"
            }
        )
        return

    player.queue.pop(target - 1)

    await request.respond(
        {
            "status": "success",
            "message": "成功移除歌曲"
        }
    )

    await player.update_display(new_message=await channel.send("Loading..."))


async def clean(client: "KavaClient", request: "Request", channel_id: int):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    player: LavaPlayer = client.bot.lavalink.player_manager.get(channel.guild.id)

    if not player.is_playing:
        await request.respond(
            {
                "status": "error",
                "message": "沒有正在播放的歌曲"
            }
        )
        return

    player.queue.clear()

    await request.respond(
        {
            "status": "success",
            "message": "成功清空播放序列"
        }
    )

    await player.update_display(new_message=await channel.send("Loading..."))


async def pause(client: "KavaClient", request: "Request", channel_id: int):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    player: LavaPlayer = client.bot.lavalink.player_manager.get(channel.guild.id)

    if not player.is_playing:
        await request.respond(
            {
                "status": "error",
                "message": "沒有正在播放的歌曲"
            }
        )
        return

    await player.set_pause(True)

    await request.respond(
        {
            "status": "success",
            "message": "成功暫停播放"
        }
    )

    await player.update_display(new_message=await channel.send("Loading..."))


async def resume(client: "KavaClient", request: "Request", channel_id: int):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    player: LavaPlayer = client.bot.lavalink.player_manager.get(channel.guild.id)

    if not player.is_playing:
        await request.respond(
            {
                "status": "error",
                "message": "沒有正在播放的歌曲"
            }
        )
        return

    await player.set_pause(False)

    await request.respond(
        {
            "status": "success",
            "message": "成功恢復播放"
        }
    )

    await player.update_display(new_message=await channel.send("Loading..."))


async def stop(client: "KavaClient", request: "Request", channel_id: int):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    player: LavaPlayer = client.bot.lavalink.player_manager.get(channel.guild.id)

    if not player.is_playing:
        await request.respond(
            {
                "status": "error",
                "message": "沒有正在播放的歌曲"
            }
        )
        return

    await player.stop()
    player.queue.clear()

    await channel.guild.voice_client.disconnect(force=False)

    await player.update_display(new_message=await channel.send("Loading..."))

    await request.respond(
        {
            "status": "success",
            "message": "成功停止播放並清空播放序列"
        }
    )


async def queue(client: "KavaClient", request: "Request", channel_id: int):
    if not (channel := await ensure_channel(request, channel_id)):
        return

    player: LavaPlayer = client.bot.lavalink.player_manager.get(channel.guild.id)

    await request.respond(
        {
            "status": "success",
            "queue": [track.title for track in player.queue]
        }
    )


def add_handlers(client: "KavaClient"):
    """
    Convenience function to add handlers from this file to the KavaClient.
    """
    client.add_handler("get_client_info", get_client_info)
    client.add_handler("connect", connect)
    client.add_handler("nowplaying", nowplaying)
    client.add_handler("play", play)
    client.add_handler("search", search)
    client.add_handler("skip", skip)
    client.add_handler("remove", remove)
    client.add_handler("clean", clean)
    client.add_handler("pause", pause)
    client.add_handler("resume", resume)
    client.add_handler("stop", stop)
    client.add_handler("queue", queue)
