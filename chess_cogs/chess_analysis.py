import discord
from discord.ext import commands
from discord import app_commands
from datetime import date
import requests
from stockfish.stockfish import Stockfish

class ChessComDAO():
    def __init__(self) -> None:
        self._headers: dict = {
            'User-Agent': 'SZACH',
        }
        self._url: str = "https://api.chess.com/pub/player/{user}/games/{y}/{m:02d}"

    def get_last_match(self, user: str) -> dict:
        today: date = date.today()
        url: str = self._url.format(user=user, y=today.year, m=today.month)
        response: requests.Response = requests.get(url, headers=self._headers)
        if response.status_code == 200:
            jazon = response.json()
            if jazon['games']:
                return jazon['games'][0]

        return {}


class Analysis(commands.Cog):
    def __init__(self, bot, stockfish: Stockfish) -> None:
        self.bot: commands.Bot = bot
        self._chess_dao: ChessComDAO = ChessComDAO()
        self.stockfish = stockfish
        self._results_dir = 'results'

    async def _analysis_helper(self, interaction, game_info: str):
        scores = self.stockfish.analise_match(game_info['pgn'])
        results: dict = {'analysis': scores}
        filename = f'{self._results_dir}/analysis_result_{game_info['uuid']}.txt'
        with open(filename, "w") as file:
            file.write(str(results))
        
        with open(filename, "rb") as file:
            await interaction.followup.send("Your analysis is:", file=discord.File(file, filename))


    @app_commands.command(name='analysis')
    @app_commands.describe(username='chess.com username')
    async def analyse(self, interaction: discord.Interaction, username: str):
        """
        Sends analysis of last match played by chess.com user.

        :param username: chees.com username
        """
        await interaction.response.defer()
        game_info: dict = self._chess_dao.get_last_match(username)
        if game_info:
            await interaction.followup.send(
                f'Requested chess game analysis:\n'+ 
                f'Game url: {game_info['url']}\n' +
                f'White: {game_info['white']['username']} with {game_info['white']['rating']} ELO; **{game_info['white']['result']}**\n' +
                f'Black: {game_info['black']['username']} with {game_info['black']['rating']} ELO; **{game_info['black']['result']}**\n' +
                f'Analisys will be sent shortly'
            )
            self.bot.loop.create_task(self._analysis_helper(interaction, game_info))

        else:
            await interaction.followup.send(f'There are no games to analyse.')