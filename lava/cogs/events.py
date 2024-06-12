from logging import getLogger

from disnake import MessageInteraction
from disnake.ext import commands
from disnake.ext.commands import Cog, CommandInvokeError
from lavalink import TrackEndEvent, TrackLoadFailedEvent, QueueEndEvent, TrackStartEvent, PlayerUpdateEvent

from lava.bot import Bot
from lava.classes.player import LavaPlayer
from lava.embeds import ErrorEmbed
from lava.errors import MissingVoicePermissions, BotNotInVoice, UserNotInVoice, UserInDifferentChannel
from lava.krabbe.utils import can_use_music
from lava.utils import ensure_voice


class Events(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.logger = getLogger("lava.events")

    async def cog_load(self):
        await self.bot.wait_until_ready()

    @Cog.listener(name="on_ready")
    async def on_ready(self):
        self.bot.lavalink.add_event_hook(self.on_player_update, event=PlayerUpdateEvent)
        self.bot.lavalink.add_event_hook(self.on_track_end, event=TrackEndEvent)
        self.bot.lavalink.add_event_hook(self.on_queue_end, event=QueueEndEvent)
        self.bot.lavalink.add_event_hook(self.on_track_load_failed, event=TrackLoadFailedEvent)

    async def on_player_update(self, event: PlayerUpdateEvent):
        player: LavaPlayer = event.player

        self.bot.logger.info("Received player update event for guild %s", player.guild)

        try:
            await player.update_display()
        except ValueError:
            pass

    async def on_track_end(self, event: TrackEndEvent):
        player: LavaPlayer = event.player

        self.bot.logger.info("Received track end event for guild %s", player.guild)

        try:
            await player.update_display()
        except ValueError:
            pass

    async def on_queue_end(self, event: QueueEndEvent):
        player: LavaPlayer = event.player

        self.bot.logger.info("Received queue end event for guild %s", player.guild)

        await player.guild.voice_client.disconnect(force=False)

    async def on_track_load_failed(self, event: TrackLoadFailedEvent):
        player: LavaPlayer = event.player

        self.bot.logger.info("Received track load failed event for guild %s", player.guild)

        message = await player.message.channel.send(
            embed=ErrorEmbed(
                f"無法播放歌曲: {event.track['title']}",
                f"原因: `{event.original or 'Unknown'}`"
            )
        )
        await player.skip()
        await player.update_display(message, delay=5)

    @commands.Cog.listener(name="on_voice_state_update")
    async def on_voice_state_update(self, member, before, after):
        if (
                before.channel is not None
                and after.channel is None
                and member.id == self.bot.user.id
        ):
            player = self.bot.lavalink.player_manager.get(member.guild.id)

            if player is not None:
                await player.stop()
                player.queue.clear()

                try:
                    await player.update_display()
                except ValueError:  # There's no message to update
                    pass

    @commands.Cog.listener(name="on_message_interaction")
    async def on_message_interaction(self, interaction: MessageInteraction):
        if not interaction.data.custom_id.startswith("control"):
            return

        if interaction.data.custom_id.startswith("control.empty"):
            await interaction.response.edit_message()
            return

        try:
            await ensure_voice(interaction, should_connect=False)
        except (UserNotInVoice, BotNotInVoice, MissingVoicePermissions, UserInDifferentChannel):
            return

        if not await can_use_music(self.bot.kava_client, interaction.author.id, interaction.author.voice.channel.id):
            await interaction.response.send_message(
                embed=ErrorEmbed("此語音頻道擁有者不允許其他成員使用音樂功能"),
                ephemeral=True
            )
            return

        player = self.bot.lavalink.player_manager.get(interaction.guild_id)

        match interaction.data.custom_id:
            case "control.resume":
                await player.set_pause(False)

            case "control.pause":
                await player.set_pause(True)

            case "control.stop":
                await player.stop()
                player.queue.clear()
                await interaction.guild.voice_client.disconnect(force=False)

            case "control.previous":
                await player.seek(0)

            case "control.next":
                await player.skip()

            case "control.shuffle":
                player.set_shuffle(not player.shuffle)

            case "control.repeat":
                player.set_loop(player.loop + 1 if player.loop < 2 else 0)

            case "control.rewind":
                await player.seek(round(player.position) - 10000)

            case "control.forward":
                await player.seek(round(player.position) + 10000)

        await player.update_display(interaction=interaction)


def setup(bot):
    bot.add_cog(Events(bot))
