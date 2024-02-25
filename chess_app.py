import os
import discord
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from chess_cogs.greeting import Greeting
from chess_cogs.music import Music

# load Discord bot token from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
print(TOKEN)

# select intents/permissions for bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='DJ SZACH Z ODSŁONY WJEŻDZA NA SALONY',
    intents=intents,
)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


async def main():
    async with bot:
        # add cogs
        await bot.add_cog(Greeting(bot))
        await bot.add_cog(Music(bot))
        # launch app with saved token
        await bot.start(TOKEN)


asyncio.run(main())
