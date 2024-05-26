import asyncio
from time import time
from typing import TYPE_CHECKING, Optional, Union

from disnake import Message, Locale, ButtonStyle, Embed, Colour, Guild, Interaction
from disnake.ui import ActionRow, Button
from lavalink import DefaultPlayer, Node, parse_time

from lava.utils import get_image_size

if TYPE_CHECKING:
    from lava.bot import Bot


class LavaPlayer(DefaultPlayer):
    def __init__(self, bot: "Bot", guild_id: int, node: Node):
        super().__init__(guild_id, node)

        self.bot: Bot = bot
        self.message: Optional[Message] = None
        self.locale: Locale = Locale.zh_TW

        self._guild: Optional[Guild] = None

        self.autoplay: bool = False

        self._last_update: int = 0
        self._last_position = 0
        self.position_timestamp = 0

        self.__display_image_as_wide: Optional[bool] = None
        self.__last_image_url: str = ""

    @property
    def guild(self) -> Optional[Guild]:
        if not self._guild:
            self._guild = self.bot.get_guild(self.guild_id)

        return self._guild

    async def update_display(self,
                             new_message: Optional[Message] = None,
                             delay: int = 0,
                             interaction: Optional[Interaction] = None,
                             locale: Optional[Locale] = None) -> None:
        """
        Update the display of the current song.

        Note: If new message is provided, Old message will be deleted after 5 seconds

        :param new_message: The new message to update the display with, None to use the old message.
        :param delay: The delay in seconds before updating the display.
        :param interaction: The interaction to be responded to.
        :param locale: The locale to use for the display
        """
        if interaction:
            self.locale = interaction.locale

        if locale:
            self.locale = locale

        self.bot.logger.info(
            "Updating display for player in guild %s in a %s seconds delay", self.bot.get_guild(self.guild_id), delay
        )

        await asyncio.sleep(delay)

        if not self.message and not new_message:
            self.bot.logger.warning(
                "No message to update display for player in guild %s", self.bot.get_guild(self.guild_id)
            )
            return

        if new_message:
            try:
                self.bot.logger.debug(
                    "Deleting old existing display message for player in guild %s", self.bot.get_guild(self.guild_id)
                )

                _ = self.bot.loop.create_task(self.message.delete())
            except (AttributeError, UnboundLocalError):
                pass

            self.message = new_message

        if not self.is_connected or not self.current:
            components = []

        else:
            components = [
                ActionRow(
                    Button(
                        style=ButtonStyle.green,
                        emoji=self.bot.get_icon('control.pause', "⏸️"),
                        custom_id="control.pause",
                        label="暫停"
                    ) if not self.paused else Button(
                        style=ButtonStyle.red,
                        emoji=self.bot.get_icon('control.resume', "▶️"),
                        custom_id="control.resume",
                        label="繼續"
                    ),
                    Button(
                        style=ButtonStyle.blurple,
                        emoji=self.bot.get_icon('control.previous', "⏮️"),
                        custom_id="control.previous",
                        label="重新開始"
                    ),
                    Button(
                        style=ButtonStyle.blurple,
                        emoji=self.bot.get_icon('control.next', "⏭️"),
                        custom_id="control.next",
                        label="跳過"
                    )
                ),
                ActionRow(
                    Button(
                        style=ButtonStyle.red,
                        emoji=self.bot.get_icon('control.stop', "⏹️"),
                        custom_id="control.stop",
                        label="停止"
                    ),
                    Button(
                        style=ButtonStyle.blurple,
                        emoji=self.bot.get_icon('control.rewind', "⏪"),
                        custom_id="control.rewind",
                        label="倒帶十秒"
                    ),
                    Button(
                        style=ButtonStyle.blurple,
                        emoji=self.bot.get_icon('control.forward', "⏩"),
                        custom_id="control.forward",
                        label="快進十秒"
                    )
                ),
                ActionRow(
                    Button(
                        style=ButtonStyle.green if self.shuffle else ButtonStyle.grey,
                        emoji=self.bot.get_icon('control.shuffle', "🔀"),
                        custom_id="control.shuffle",
                        label="隨機播放"
                    ),
                    Button(
                        style=[ButtonStyle.grey, ButtonStyle.green, ButtonStyle.blurple][self.loop],
                        emoji=self.bot.get_icon('control.repeat', "🔁"),
                        custom_id="control.repeat",
                        label="重複播放"
                    )
                )
            ]

        if interaction:
            await interaction.response.edit_message(
                content=None, embed=await self.__generate_display_embed(), components=components
            )

        else:
            await self.message.edit(content=None, embed=(await self.__generate_display_embed()), components=components)

        self.bot.logger.debug(
            "Updating player in guild %s display message to %s", self.bot.get_guild(self.guild_id), self.message.id
        )

    async def __generate_display_embed(self) -> Embed:
        """
        Generate the display embed for the player.

        :return: The generated embed
        """
        embed = Embed()

        if self.is_playing:
            embed.set_author(
                name='播放中',
                icon_url="https://cdn.discordapp.com/emojis/987643956403781692.webp"
            )

            embed.colour = Colour.green()

        elif self.paused:
            embed.set_author(
                name='已暫停',
                icon_url="https://cdn.discordapp.com/emojis/987661771609358366.webp"
            )

            embed.colour = Colour.orange()

        elif not self.is_connected:
            embed.set_author(
                name='已斷線',
                icon_url="https://cdn.discordapp.com/emojis/987646268094439488.webp"
            )

            embed.colour = Colour.red()

        elif not self.current:
            embed.set_author(
                name='已結束',
                icon_url="https://cdn.discordapp.com/emojis/987645074450034718.webp"
            )

            embed.colour = Colour.red()

        loop_mode_text = {
            0: '關閉',
            1: '單曲',
            2: '整個序列'
        }

        if self.current:
            embed.title = self.current.title
            embed.description = f"`{self.__format_time(self.position)}`" \
                                f" {self.__generate_progress_bar(self.current.duration, self.position)} " \
                                f"`{self.__format_time(self.current.duration)}`"

            embed.add_field(
                name='👤 作者', value=self.current.author, inline=True
            )

            embed.add_field(
                name='👥 點播者',
                value="自動播放" if not self.current.requester else f"<@{self.current.requester}>",
                inline=True
            )

            embed.add_field(
                name='🔁 重複播放模式',
                value=loop_mode_text[self.loop],
                inline=True
            )

            queue_titles = [f"**[{index + 1}]** {track.title}" for index, track in enumerate(self.queue[:5])]
            queue_display = '\n'.join(queue_titles)

            if len(self.queue) > 5:
                queue_display += f"\n{'還有更多...'}"

            embed.add_field(
                name='📃 播放序列',
                value=queue_display or '空',
                inline=True
            )

            embed.add_field(
                name='🔀 隨機播放',
                value='開啟'
                if self.shuffle else '關閉',
                inline=True
            )

            if self.current.artwork_url:
                if await self.is_current_artwork_wide():
                    embed.set_image(self.current.artwork_url)
                else:
                    embed.set_thumbnail(self.current.artwork_url)

        else:
            embed.title = '沒有正在播放的音樂'

        return embed

    @staticmethod
    def __format_time(time_ms: Union[float, int]) -> str:
        """
        Formats the time into DD:HH:MM:SS

        :param time_ms: Time in milliseconds
        :return: Formatted time
        """
        days, hours, minutes, seconds = parse_time(round(time_ms))

        days, hours, minutes, seconds = map(round, (days, hours, minutes, seconds))

        return ((f"{str(hours).zfill(2)}:" if hours else "")
                + f"{str(minutes).zfill(2)}:{str(seconds).zfill(2)}")

    def __generate_progress_bar(self, duration: Union[float, int], position: Union[float, int]):
        """
        Generate a progress bar.

        :param duration: The duration of the song.
        :param position: The current position of the song.
        :return: The progress bar.
        """
        duration = round(duration / 1000)
        position = round(position / 1000)

        if duration == 0:
            duration += 1

        percentage = position / duration

        return f"{self.bot.get_icon('progress.start_point', 'ST|')}" \
               f"{self.bot.get_icon('progress.start_fill', 'SF|') * round(percentage * 10)}" \
               f"{self.bot.get_icon('progress.mid_point', 'MP|') if percentage != 1 else self.bot.get_icon('progress.start_fill', 'SF|')}" \
               f"{self.bot.get_icon('progress.end_fill', 'EF|') * round((1 - percentage) * 10)}" \
               f"{self.bot.get_icon('progress.end', 'ED|') if percentage != 1 else self.bot.get_icon('progress.end_point', 'EP')}"

    async def is_current_artwork_wide(self) -> bool:
        """
        Check if the current playing track's artwork is wide.
        """
        if not self.current:
            return False

        if not self.current.artwork_url:
            return False

        if self.__last_image_url == self.current.artwork_url:
            return self.__display_image_as_wide

        self.__last_image_url = self.current.artwork_url

        width, height = await get_image_size(self.current.artwork_url)

        self.__display_image_as_wide = width > height

        return self.__display_image_as_wide

    async def _update_state(self, state: dict):
        """
        Updates the position of the player.

        Parameters
        ----------
        state: :class:`dict`
            The state that is given to update.
        """
        self._last_update = int(time() * 1000)
        self._last_position = state.get('position', 0)
        self.position_timestamp = state.get('time', 0)

        _ = self.bot.loop.create_task(self.update_display())
