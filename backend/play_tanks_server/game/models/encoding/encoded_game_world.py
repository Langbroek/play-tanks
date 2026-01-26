from dataclasses import dataclass, field
from typing import List

from play_tanks_server.game.models.encoding import EncodedGameObject, EncodedPlayer, EncodedEntity


@dataclass(frozen=True)
class EncodedGameWorld(EncodedGameObject):
    """ Encoded representation of the game world. """
    started: bool
    tick: int
    time: float
    map_size: tuple
    players: List[EncodedPlayer]
    entities: List[EncodedEntity]
    data: dict = field(default_factory=dict)