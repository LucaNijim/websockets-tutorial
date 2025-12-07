import secrets
from dataclasses import dataclass

from websockets.legacy.server import WebSocketServerProtocol

from gamelogic.connect4 import Connect4


@dataclass 
class PlayerInfo:
    role: str 
    name: str

class Room:
    """ 
    A Game Room

    it should contain:
    - the current game 
    - 

    """

    def __init__(self):
        self.game = Connect4()
        self.connections: dict[WebSocketServerProtocol, PlayerInfo] = {}
        self.spectators: set[WebSocketServerProtocol] = set()
        self.rematch_votes: set[WebSocketServerProtocol] = set()
        self.game_over = False
        self.record: list[dict] = []
        self.watch_key = secrets.token_urlsafe(8)
        