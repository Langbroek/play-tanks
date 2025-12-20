from dataclasses import dataclass
from typing import Generic, Optional
from typing_extensions import Self, TypeVar

from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.objects import Entity


T = TypeVar('T', default=Entity, bound=Entity)


@dataclass
class CollisionEvent(Generic[T]):
    source: T
    target: Optional[Entity]
    distance: float
    collision_normal: Optional[Vec2] = None
    collision_point: Optional[Vec2] = None
    recompute: bool = False

    def __lt__(self, other: Self) -> bool:
        return self.distance < other.distance
    

