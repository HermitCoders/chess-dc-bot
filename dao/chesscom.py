from datetime import date
import requests


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
