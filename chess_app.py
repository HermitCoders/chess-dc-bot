import os
import discord
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from chess_cogs.greeting import Greeting
from chess_cogs.music import Music
from chess_cogs.chess_analysis import Analysis
from stockfish.stockfish import Stockfish

# discord.utils.setup_logging(level=logging.DEBUG, root=False)
# load Discord bot token from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
STOCKFISH_PATH = os.getenv('STOCKFISH_PATH')
GUILD_ID = os.getenv('GUILD_ID')

# create guild ID
guild = discord.Object(id=GUILD_ID)

# select intents/permissions for bot
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='DJ SZACH Z ODSŁONY WJEŻDZA NA SALONY',
    intents=intents,
)

@bot.event
async def on_ready():
    synced = await bot.tree.sync(guild=guild)
    print(f'Logged in as {bot.user} (ID: {bot.user.id}) and synced {len(synced)} commands')
    print('------')

async def main():
    async with bot:
        # add cogs
        await bot.add_cog(Greeting(bot))
        await bot.add_cog(Music(bot), guild=guild)
        await bot.add_cog(Analysis(bot, stockfish=Stockfish(stockfish_path=STOCKFISH_PATH)), guild=guild)
        # launch app with saved token
        await bot.start(TOKEN)

asyncio.run(main())
