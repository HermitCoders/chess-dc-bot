import os
import discord
from dotenv import load_dotenv

# load Discord bot token from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
print(TOKEN)

# select intents/permissions for bot
intents = discord.Intents.default()
intents.message_content = True

# create basic connection to Discord
client = discord.Client(intents=intents)

# register basic callbacks
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

# launch app with saved token
client.run(TOKEN)