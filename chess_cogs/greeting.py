import discord
from discord.ext import commands

class Greeting(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self._last_member = None

    @commands.command()
    async def hello(self, ctx, *, member: discord.Member = None):
        member = member or ctx.author
        if self._last_member is None or self._last_member.id != member.id:
            await ctx.send(f'Hello {member.name}~')
        else:
            await ctx.send(f'Hello {member.name}... This feels familiar.')
        self._last_member = member
