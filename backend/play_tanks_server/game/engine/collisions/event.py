from dataclasses import dataclass, field
from typing import Optional, Generic, List
from typing_extensions import Self, TypeVar

from play_tanks_server.game.engine.math import Transform
from play_tanks_server.game.engine.math.shapes import Rectangle
from play_tanks_server.game.engine.collisions import Intersections2D
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
        return self.intersections.time
    
    @property
    def stale(self) -> bool:
        """ Returns if the collision intersection is stale. """
        if self.time < 0:
            return True
        return self.time_at_intersection == self.time

    def __lt__(self, other: Self) -> bool:
        if self.time_at_intersection == other.time_at_intersection:
            return self.time < other.time
        return self.time_at_intersection < other.time_at_intersection
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CollisionEvent):
            return False
        return other is self

    def __hash__(self) -> int:
        return hash(id(self))