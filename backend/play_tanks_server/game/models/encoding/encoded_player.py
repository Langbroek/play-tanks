from dataclasses import dataclass, field

from play_tanks_server.game.models.encoding import EncodedGameObject


@dataclass(frozen=True)
class EncodedPlayer(EncodedGameObject):
    """ Serialisable player data for visualisation. """
    name: str
    data: dict = field(default_factory=dict)
