from dataclasses import dataclass, field
from typing import Optional, Generic, List
from typing_extensions import Self, TypeVar

from play_tanks_server.game.engine.math import Transform
from play_tanks_server.game.engine.math.shapes import Rectangle
from play_tanks_server.game.models.collisions import Intersections2D
from play_tanks_server.game.objects import Entity


T = TypeVar('T', bound=Entity, default=Entity)


@dataclass
class CollisionEvent(Generic[T]):
    entity: T
    aabb: Rectangle
    time: float = 0.0
    intersections: Intersections2D = field(default_factory=Intersections2D)
    transform: Optional[Transform] = None
    static: bool = False
    
    @property
    def time_at_intersection(self) -> float:
        """ Returns the time until intersection occurs. """
        if self.intersections is not None:
            return self.intersections.time
        return -1.0

    def __lt__(self, other: Self) -> bool:
        return self.time_at_intersection < other.time_at_intersection
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CollisionEvent):
            return False
        return other is self

    def __hash__(self) -> int:
        return hash(id(self))