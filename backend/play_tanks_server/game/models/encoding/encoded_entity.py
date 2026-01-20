from dataclasses import dataclass, field

from play_tanks_server.game.models.encoding import EncodedGameObject


@dataclass(frozen=True)
class EncodedEntity(EncodedGameObject):
    """ Serialisable entity data for visualisation. """
    uid: str
    type: str
    x: float
    y: float
    width: float
    length: float
    height: float
    rotation: float
    dir_x: float
    dir_y: float
    data: dict = field(default_factory=dict)