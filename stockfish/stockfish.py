import chess
import chess.engine
import chess.pgn
import io

class Stockfish():
    def __init__(self, stockfish_path: str, time_limit: float = 0.1) -> None:
        self._stockfish_path = stockfish_path
        self._time_limit = time_limit

    def analise_match(self, match_pgn: str):
        engine = chess.engine.SimpleEngine.popen_uci(self._stockfish_path)
        game = chess.pgn.read_game(io.StringIO(match_pgn))
        board = game.board()
        scores = []
        for move in game.mainline_moves():
            board.push(move)
            info = engine.analyse(board, chess.engine.Limit(time=self._time_limit))
            scores.append((str(move), info['score'].white().score()))

        engine.quit()

        return scores
