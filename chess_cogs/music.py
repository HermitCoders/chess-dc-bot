import asyncio
import discord
import yt_dlp as youtube_dl

from discord.ext import commands
from queue import Queue

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
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
                player: discord.PCMVolumeTransformer = await YTDLSource.from_url(song_data['original_url'], loop=self.bot.loop, volume=self._current_volume)
                ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else self.bot.loop.create_task(self.play_next_song(ctx)))
                await ctx.send(f'From queue, now playing: {player.title}')
                print(f'From queue, now playing: {player.title}')
            else:
                await ctx.send(f'Queue is empty')
                print(f'Queue is empty')

    @commands.command()
    async def qPlaylist(self, ctx, *, url):
        """"Enables queue and adds songs from playlist to queue"""
        self._queue_enabled = True
        async with ctx.typing():    
            playlist_data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            for song_data in playlist_data['entries']:
                self._song_queue.put(song_data)
            await ctx.send(f'Queued: playlist **{playlist_data['title']}** with **{len(playlist_data['entries'])}** songs')
            print(f'Queued: playlist {playlist_data['title']} with {len(playlist_data['entries'])} songs')

            if not ctx.voice_client.is_playing():
                await self.play_next_song(ctx)

    @commands.command()
    async def qAdd(self, ctx, *, url):
        """Enables queue and adds song to queue"""
        self._queue_enabled = True

        async with ctx.typing():    
            song_data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            self._song_queue.put(song_data)
        await ctx.send(f'Queued: **{song_data['title']}**')
        print(f'Queued: {song_data['title']}')

        if not ctx.voice_client.is_playing():
            await self.play_next_song(ctx)

    @commands.command()
    async def qSkip(self, ctx):
        """Skips current song and plays next in queue"""
        vc: discord.VoiceClient = ctx.voice_client
        if vc.is_playing():
            async with ctx.typing(): 
                vc.stop()   
            await ctx.send(f'Skipped: **{vc.source.title}**')
            print(f'Skipped: {vc.source.title}')

    @commands.command()
    async def qClear(self, ctx):
        """Clears queue"""
        with self._song_queue.mutex:
            self._song_queue.queue.clear()
        await ctx.send(f'Queue was cleared')
        print(f'Queue was cleared')

    @commands.command()
    async def qOff(self, ctx):
        """Disables and clears queue"""
        self._queue_enabled = False

        with self._song_queue.mutex:
            self._song_queue.queue.clear()
        await ctx.send(f'Queue was cleared and disabled')
        print(f'Queue was cleared and disabled')

    @commands.command()
    async def qShow(self, ctx):
        """Shows queue"""
        with self._song_queue.mutex:
            queue = list(self._song_queue.queue)
            if len(queue) > 0:
                msg = "\n- ".join([song['title'] for song in queue])
                await ctx.send(f'Current queue:\n- {msg}')
            else:
                await ctx.send(f'Current queue is empty')

        print(f'Queue was showed')

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""
        voice = None
        if ctx.voice_client is not None:
            voice = await ctx.voice_client.move_to(channel)
        else:
            voice = await channel.connect()
        
        print(f'Joined {channel.name} channel')
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("X2Download.app - Alright let's do this (Counter Strike Bot Call) - Sound Effect for editing (320 kbps).mp3"))
        voice.play(source)

    @commands.command()
    async def play(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query), volume=self._current_volume)
        ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else self.play_next_song(ctx))

        await ctx.send(f'Now playing: {query}')
        print(f'Now playing: {query}')

    @commands.command()
    async def yt(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, volume=self._current_volume)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else self.play_next_song(ctx))

        await ctx.send(f'Now playing: {player.title}')
        print(f'Now playing: {player.title}')

    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True, volume=self._current_volume)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else self.play_next_song(ctx))

        await ctx.send(f'Now playing: {player.title}')
        print(f'Now playing: {player.title}')

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

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
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()
        print("Voice channel disconnected")

    @commands.command()
    async def stop(self, ctx):
        """Stops playing audio"""
        vc: discord.VoiceClient = ctx.voice_client
        self._queue_enabled = False

        if vc is None:
            return await ctx.send("Not connected to a voice channel.")

        if vc.is_playing():
            async with ctx.typing():
                vc.stop()
            await ctx.send(f'Stopped audio')
            print("Stopped audio")
        else:
            await ctx.send(f'Nothing\' playin\' mate')
            print("Audio is already stopped/paused")

    @commands.command()
    async def resume(self, ctx):
        """Resumes playing audio"""
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
        """Pauses playing audio"""
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

    @play.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice_stop_current_song(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @qAdd.before_invoke
    @qPlaylist.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")

    @commands.command()
    async def helpMusic(self, ctx):
        """Displays detailed music help"""
        help_msg = """
# Hello there!
This bot has several commands that you can use, let's divide them into three groups, each for managing:
- connection,
- audio source,
- audio itself,
- queue.

## Connection commands:
- !join **voice-channel-name** - joins voice channel with specified name (case sensitive) and greets other channel members;
- !kill - stops audio and disconnects bot from voice channel.

## Audio source commands:
- !yt **youtube-url** - downloads audio from url to bot's host filesystem and then plays it in the voice channel;
- !stream **youtube-url** - same as above, but audio is streamed;
- !play **path-to-file** - plays a file from host filesystem.
Each command can be executed only if user is connected to a voice channel.
If user is in a voice channel and uses any of audio source commands, bot joins user in that voice channel.

## Audio manipulation:
- !volume **integer from 0 to 100** - sets audio volume to specific number;
- !stop - stops audio, removes it from player, cannot be resumed;
- !pause - pauses audio;
- !resumed - resumes audio.

## Queue manipulation:
- !qAdd **youtube-utl** - enables queue and adds song to queue, plays it if it is the first in queue;
- !qSkip - skips current song, plays next one in queue;
- !qShow - shows current queue;
- !qClear - clears queue;
- !qOff - clears and disables queue;
        """
        await ctx.send(help_msg)
        print("Showed help")
