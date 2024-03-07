
import discord
import yt_dlp as youtube_dl
from discord.ext import commands
from queue import Queue
from discord import app_commands
from dao.youtube import YTDLSource, create_ytdl

ytdl = create_ytdl()

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self._current_volume = 0.02

        self._song_queue: Queue[dict] = Queue()
        self._queue_enabled: bool = False

    async def play_next_song(self, channel, voice_client):
        if self._queue_enabled:
            if not self._song_queue.empty():
                song_data: dict = self._song_queue.get()
                player: discord.PCMVolumeTransformer = await YTDLSource.from_url(song_data['url'], loop=self.bot.loop, volume=self._current_volume)
                voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else self.bot.loop.create_task(self.play_next_song(channel, voice_client)))
                await channel.send(f'From queue, now playing: **{player.title}**')
                print(f'From queue, now playing: {player.title}')
            else:
                await channel.send(f'Queue is empty')
                print(f'Queue is empty')

    async def ensure_voice(self, interaction: discord.Interaction) -> bool:
        voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice_client is None:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()
                print(f'Joined {interaction.user.voice.channel.name} channel')
                return True
            else:
                await interaction.response.send_message("You are not connected to a voice channel.")
                return False
        return True

    @app_commands.command(name='playlist')
    @app_commands.describe(url='youtube playlist url')
    async def playlist(self, interaction: discord.Interaction, url: str) -> None:
        """
        Enables queue and adds songs from playlist to queue.

        :param url: youtube url
        """
        await interaction.response.defer()
        if await self.ensure_voice(interaction):
            self._queue_enabled = True
            playlist_data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            for song_data in playlist_data['entries']:
                self._song_queue.put(song_data)
            await interaction.followup.send(f'Queued: playlist **{playlist_data['title']}** with **{len(playlist_data['entries'])}** songs')
            print(f'Queued: playlist {playlist_data['title']} with {len(playlist_data['entries'])} songs')
            
            voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
            if not voice_client.is_playing():
                await self.play_next_song(interaction.channel, voice_client)

    @app_commands.command(name='add')
    @app_commands.describe(url='youtube song url')
    async def add(self, interaction: discord.Interaction, url: str):
        """
        Enables queue and adds song to queue.

        :param url: youtube url
        """
        await interaction.response.defer()
        if await self.ensure_voice(interaction):
            self._queue_enabled = True
            song_data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            song_data['url'] = url
            self._song_queue.put(song_data)
            await interaction.followup.send(f'Queued: **{song_data['title']}**')
            print(f'Queued: {song_data['title']}')

            voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
            if not voice_client.is_playing():
                await self.play_next_song(interaction.channel, voice_client)

    @app_commands.command(name='skip')
    async def skip(self, interaction: discord.Interaction):
        """Skips current song and plays next in queue."""
        vc: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if vc.is_playing():
            title = vc.source.title
            vc.stop()   
            await interaction.response.send_message(f'Skipped: **{title}**')
            print(f'Skipped: {vc.source.title}')

    @app_commands.command(name='clear')
    async def clear(self, interaction: discord.Interaction):
        """Clears queue."""
        with self._song_queue.mutex:
            self._song_queue.queue.clear()
        await interaction.response.send_message(f'Queue was cleared')
        print(f'Queue was cleared')

    @app_commands.command(name='show')
    async def show(self, interaction: discord.Interaction):
        """Shows queue."""
        with self._song_queue.mutex:
            queue = list(self._song_queue.queue)
        song_limit = 10
        if len(queue) > 0:
            msg = "\n- ".join([song['title'] for song in queue[:song_limit]])
            if len(queue) > song_limit:
                msg = msg + f'\n- ...another {len(queue)-song_limit} songs'
            await interaction.response.send_message(f'Current queue:\n- {msg}')
        else:
            await interaction.response.send_message(f'Current queue is empty')

        print(f'Queue was showed')

    @app_commands.command(name='volume')
    @app_commands.describe(volume='integer from 1 to 100, default is 2')
    async def volume(self, interaction: discord.Interaction, volume: int = 2):
        """
        Changes the player's volume.

        :param volume: integer from 1 to 100
        """
        voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice_client is None:
            await interaction.response.send_message("Not connected to a voice channel.")
        else:
            # set volume for current song playing
            voice_client.source.volume = volume / 100
            # save volume for next song
            self._current_volume = volume / 100

            await interaction.response.send_message(f"Changed volume to **{volume}%**")
            print(f"Changed volume to {volume}%")

    @app_commands.command(name='kill')
    async def kill(self, interaction: discord.Interaction):
        """Disables and cleras queue, stops and disconnects the bot from voice."""
        await interaction.response.defer()
        vc: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        self._queue_enabled = False

        with self._song_queue.mutex:
            self._song_queue.queue.clear()

        await interaction.followup.send(f'Queue was cleared and disabled')
        print(f'Queue was cleared and disabled')

        if vc.is_playing():
            vc.stop()
            await interaction.followup.send(f'Stopped audio')
            print("Stopped audio")

        await vc.disconnect()
        print("Voice channel disconnected")

    @app_commands.command(name='resume')
    async def resume(self, interaction: discord.Interaction):
        """Resumes audio."""
        vc: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if vc is None:
            return await interaction.response.send_message("Not connected to a voice channel.")

        if vc.is_paused():
            vc.resume()
            await interaction.response.send_message(f'Resumed audio')
            print("Resumed audio")
        else:
            await interaction.response.send_message(f'Nothing\' paused\' mate')
            print("Audio is already stopped/resumed")

    @app_commands.command(name='pause')
    async def pause(self, interaction: discord.Interaction):
        """Pauses audio."""
        vc: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if vc is None:
            return await interaction.response.send_message("Not connected to a voice channel.")

        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message(f'Paused audio')
            print("Paused audio")
        else:
            await interaction.response.send_message(f'Nothing\' playin\' mate')
            print("Audio is already stopped/paused")
