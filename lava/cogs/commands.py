from os import getpid

from disnake import ApplicationCommandInteraction, Embed
from disnake.ext import commands
from disnake.ext.commands import Cog
from lavalink import Timescale, Tremolo, Vibrato, LowPass, Rotation, Equalizer
from psutil import cpu_percent, virtual_memory, Process

from lava.bot import Bot
from lava.embeds import InfoEmbed
from lava.utils import bytes_to_gb, get_commit_hash, get_upstream_url, \
    get_current_branch
from os import getpid

from disnake import ApplicationCommandInteraction, Embed
from disnake.ext import commands
from disnake.ext.commands import Cog
from lavalink import Timescale, Tremolo, Vibrato, LowPass, Rotation, Equalizer
from psutil import cpu_percent, virtual_memory, Process

from lava.bot import Bot
from lava.embeds import InfoEmbed
from lava.utils import bytes_to_gb, get_commit_hash, get_upstream_url, \
    get_current_branch

allowed_filters = {
    "timescale": Timescale,
    "tremolo": Tremolo,
    "vibrato": Vibrato,
    "lowpass": LowPass,
    "rotation": Rotation,
    "equalizer": Equalizer
}


class Commands(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.slash_command(
        name="info",
        description="顯示機器人資訊，此指令隸屬於 Krabbe 2 系統"
    )
    async def info(self, interaction: ApplicationCommandInteraction):
        embed = Embed(
            title='機器人資訊',
            color=0x2b2d31
        )

        embed.add_field(
            name='啟動時間',
            value=f"<t:{round(Process(getpid()).create_time())}:F>",
            inline=True
        )

        branch = get_current_branch()
        upstream_url = get_upstream_url(branch)

        embed.add_field(
            name='版本資訊',
            value=f"{get_commit_hash()} on {branch} from {upstream_url}",
        )

        embed.add_field(name="​", value="​", inline=True)

        embed.add_field(
            name='CPU',
            value=f"{cpu_percent()}%",
            inline=True
        )

        embed.add_field(
            name='RAM',
            value=f"{round(bytes_to_gb(virtual_memory()[3]), 1)} GB / "
                  f"{round(bytes_to_gb(virtual_memory()[0]), 1)} GB "
                  f"({virtual_memory()[2]}%)",
            inline=True
        )

        embed.add_field(name="​", value="​", inline=True)

        embed.add_field(
            name='伺服器數量',
            value=len(self.bot.guilds),
            inline=True
        )

        embed.add_field(
            name='播放器數量',
            value=len(self.bot.lavalink.player_manager.players),
            inline=True
        )

        embed.add_field(name="​", value="​", inline=True)

        await interaction.response.send_message(
            embed=embed
        )

    @commands.slash_command(
        name="ping",
        description="查看機器人延遲"
    )
    async def ping(self, interaction: ApplicationCommandInteraction):
        await interaction.response.send_message(
            embed=InfoEmbed(
                title="機器人延遲",
                description=f"{round(self.bot.latency * 1000)}ms"
            )
        )


def setup(bot):
    bot.add_cog(Commands(bot))
