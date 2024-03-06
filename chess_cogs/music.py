import asyncio
import discord
import yt_dlp as youtube_dl

from discord.ext import commands
from queue import Queue

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s/%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': False,
    'progress': True,
    'no_warnings': True,
    'extract_flat': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, volume):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, volume=volume)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._current_volume = 0.02

        self._song_queue: Queue[dict] = Queue()
        self._queue_enabled: bool = False

    async def play_next_song(self, ctx):
        if self._queue_enabled:
            if not self._song_queue.empty():
                song_data: dict = self._song_queue.get()
                player: discord.PCMVolumeTransformer = await YTDLSource.from_url(song_data['url'], loop=self.bot.loop, volume=self._current_volume)
                ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else self.bot.loop.create_task(self.play_next_song(ctx)))
                await ctx.send(f'From queue, now playing: **{player.title}**')
                print(f'From queue, now playing: {player.title}')
            else:
                await ctx.send(f'Queue is empty')
                print(f'Queue is empty')

    @commands.command(aliases=['p'])
    async def playlist(self, ctx, *, url: str):
        """
        Enables queue and adds songs from playlist to queue.

        :param url: youtube url
        """
        self._queue_enabled = True
        async with ctx.typing():    
            playlist_data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            for song_data in playlist_data['entries']:
                self._song_queue.put(song_data)
            await ctx.send(f'Queued: playlist **{playlist_data['title']}** with **{len(playlist_data['entries'])}** songs')
            print(f'Queued: playlist {playlist_data['title']} with {len(playlist_data['entries'])} songs')

            if not ctx.voice_client.is_playing():
                await self.play_next_song(ctx)

    @commands.command(aliases=['a'])
    async def add(self, ctx, *, url):
        """
        Enables queue and adds song to queue.

        :param url: youtube url
        """
        self._queue_enabled = True

        async with ctx.typing():    
            song_data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            song_data['url'] = url
            self._song_queue.put(song_data)
        await ctx.send(f'Queued: **{song_data['title']}**')
        print(f'Queued: {song_data['title']}')

        if not ctx.voice_client.is_playing():
            await self.play_next_song(ctx)

    @commands.command(aliases=['s'])
    async def skip(self, ctx):
        """Skips current song and plays next in queue."""
        vc: discord.VoiceClient = ctx.voice_client
        if vc.is_playing():
            async with ctx.typing(): 
                vc.stop()   
            await ctx.send(f'Skipped: **{vc.source.title}**')
            print(f'Skipped: {vc.source.title}')

    @commands.command()
    async def clear(self, ctx):
        """Clears queue."""
        with self._song_queue.mutex:
            self._song_queue.queue.clear()
        await ctx.send(f'Queue was cleared')
        print(f'Queue was cleared')

    @commands.command()
    async def show(self, ctx):
        """Shows queue."""
        with self._song_queue.mutex:
            queue = list(self._song_queue.queue)
        song_limit = 10
        if len(queue) > 0:
            msg = "\n- ".join([song['title'] for song in queue[:song_limit]])
            if len(queue) > song_limit:
                msg = msg + "\n- ..."
            await ctx.send(f'Current queue:\n- {msg}')
        else:
            await ctx.send(f'Current queue is empty')

        print(f'Queue was showed')

    @commands.command(aliases=['v'])
    async def volume(self, ctx, volume: int):
        """
        Changes the player's volume.

        :param volume: integer from 1 to 100
        """

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        # set volume for current song playing
        ctx.voice_client.source.volume = volume / 100
        # save volume for next song
        self._current_volume = volume / 100

        await ctx.send(f"Changed volume to **{volume}%**")
        print(f"Changed volume to {volume}%")

    @commands.command()
    async def kill(self, ctx):
        """Disables and cleras queue, stops and disconnects the bot from voice."""
        vc: discord.VoiceClient = ctx.voice_client
        self._queue_enabled = False

        with self._song_queue.mutex:
            self._song_queue.queue.clear()

        await ctx.send(f'Queue was cleared and disabled')
        print(f'Queue was cleared and disabled')

        if vc.is_playing():
            async with ctx.typing():
                vc.stop()
            await ctx.send(f'Stopped audio')
            print("Stopped audio")

        await ctx.voice_client.disconnect()
        print("Voice channel disconnected")

    @commands.command()
    async def resume(self, ctx):
        """Resumes audio."""
        vc: discord.VoiceClient = ctx.voice_client
        if vc is None:
            return await ctx.send("Not connected to a voice channel.")

        if vc.is_paused():
            async with ctx.typing():
                vc.resume()
            await ctx.send(f'Resumed audio')
            print("Resumed audio")
        else:
            await ctx.send(f'Nothing\' paused\' mate')
            print("Audio is already stopped/resumed")

    @commands.command()
    async def pause(self, ctx):
        """Pauses audio."""
        vc: discord.VoiceClient = ctx.voice_client
        if vc is None:
            return await ctx.send("Not connected to a voice channel.")

        if vc.is_playing():
            async with ctx.typing():
                vc.pause()
            await ctx.send(f'Paused audio')
            print("Paused audio")
        else:
            await ctx.send(f'Nothing\' playin\' mate')
            print("Audio is already stopped/paused")

    @add.before_invoke
    @playlist.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                voice = await ctx.author.voice.channel.connect()
                print(f'Joined {ctx.author.voice.channel.name} channel')
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("X2Download.app - Alright let's do this (Counter Strike Bot Call) - Sound Effect for editing (320 kbps).mp3"))
                voice.play(source)
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
