from typing import Optional

from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.objects import GameObject
from play_tanks_server.game.models.encoding import EncodedPlayer


class Player(GameObject):

    def __init__(self, username: str, spawn: Optional[Vec2] = None):
        super().__init__()
        self.username = username
        self.spawn_position = Vec2(0, 0) if spawn is None else spawn

    def encode(self) -> EncodedPlayer:
        """ Encoding representation of the player. """
        return EncodedPlayer(
            uid=self.uid,
            name=self.username,
        )