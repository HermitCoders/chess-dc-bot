import asyncio
import yt_dlp as youtube_dl
import discord

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

def create_ytdl():
    ytdl_format_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s/%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': False,
        'progress': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
    }


    return youtube_dl.YoutubeDL(ytdl_format_options)


ffmpeg_options = {
    'options': '-vn',
}

ytdl = create_ytdl()


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
