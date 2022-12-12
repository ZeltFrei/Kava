from typing import Union

import lavalink
from disnake import TextChannel, Thread, Message, InteractionResponded, ApplicationCommandInteraction, \
    MessageInteraction
from disnake.abc import GuildChannel
from disnake.ext import commands
from disnake.ext.commands import Cog, CommandInvokeError
from lavalink import QueueEndEvent, TrackLoadFailedEvent, DefaultPlayer, PlayerUpdateEvent

from core.classes import Bot
from core.embeds import ErrorEmbed
from library.errors import MissingVoicePermissions, BotNotInVoice, UserNotInVoice, UserInDifferentChannel
from library.functions import update_display


class Events(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        lavalink.add_event_hook(self.track_hook)

    async def track_hook(self, event):
        if isinstance(event, PlayerUpdateEvent):
            player: DefaultPlayer = event.player

            try:
                await update_display(self.bot, player)
            except ValueError:
                pass

        elif isinstance(event, QueueEndEvent):
            # When this track_hook receives a "QueueEndEvent" from lavalink.py
            # it indicates that there are no tracks left in the player's queue.
            # To save on resources, we can tell the bot to disconnect from the voice channel.
            guild_id = event.player.guild_id

            guild = self.bot.get_guild(guild_id)

            try:
                await guild.voice_client.disconnect(force=True)
            except AttributeError:
                pass

        elif isinstance(event, TrackLoadFailedEvent):
            player: DefaultPlayer = event.player

            # noinspection PyTypeChecker
            channel: Union[GuildChannel, TextChannel, Thread] = self.bot.get_channel(int(player.fetch("channel")))

            # noinspection PyTypeChecker
            message: Message = await channel.fetch_message(int(player.fetch("message")))

            await channel.send(
                embed=ErrorEmbed(f"無法播放歌曲: {event.track.data['title']}"),
                reference=message
            )

            await update_display(self.bot, player, message)

    @commands.Cog.listener(name="on_slash_command_error")
    async def on_slash_command_error(self, interaction: ApplicationCommandInteraction, error: CommandInvokeError):
        if isinstance(error.original, MissingVoicePermissions):
            embed = ErrorEmbed("指令錯誤", "我需要 `連接` 和 `說話` 權限才能夠播放音樂")

        elif isinstance(error.original, BotNotInVoice):
            embed = ErrorEmbed("指令錯誤", "我沒有連接到一個語音頻道")

        elif isinstance(error.original, UserNotInVoice):
            embed = ErrorEmbed("指令錯誤", "你沒有連接到一個語音頻道")

        elif isinstance(error.original, UserInDifferentChannel):
            embed = ErrorEmbed("指令錯誤", f"你必須與我在同一個語音頻道 <#{error.original.voice.id}>")

        else:
            raise error.original

        try:
            await interaction.response.send_message(embed=embed)
        except InteractionResponded:
            await interaction.edit_original_response(embed=embed)

    @commands.Cog.listener(name="on_voice_state_update")
    async def on_voice_state_update(self, member, before, after):
        if (
                before.channel is not None
                and after.channel is None
                and member.id == self.bot.user.id
        ):
            player: DefaultPlayer = self.bot.lavalink.player_manager.get(member.guild.id)

            await player.stop()

            try:
                await update_display(self.bot, player)
            except ValueError:  # There's no message to update
                pass

    @commands.Cog.listener(name="on_message_interaction")
    async def on_message_interaction(self, interaction: MessageInteraction):
        if interaction.data.custom_id.startswith("control"):
            if interaction.data.custom_id.startswith("control.empty"):
                await interaction.response.edit_message()

                return

            player: DefaultPlayer = self.bot.lavalink.player_manager.get(interaction.guild_id)

            await interaction.response.edit_message()

            match interaction.data.custom_id:
                case "control.resume":
                    await player.set_pause(False)

                case "control.pause":
                    await player.set_pause(True)

                case "control.stop":
                    await player.stop()

                    try:
                        await interaction.guild.voice_client.disconnect(force=True)
                    except AttributeError:
                        pass

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

            await update_display(self.bot, player)


def setup(bot):
    bot.add_cog(Events(bot))
