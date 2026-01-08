from dataclasses import dataclass, field
from typing import Optional, List

from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.engine.math.shapes import Segment
from play_tanks_server.game.objects import Entity


@dataclass
class Intersection2D:
    """ Collision event for collision detection. """
    time: float = -1.0  # No interesction
    target: Optional[Entity] = None
    hulls: List[Segment] = field(default_factory=list)
    point: Optional[Vec2] = None
    invert_normal: bool = False
    illegal: bool = False
    
    def get_normals(self) -> List[Vec2]:
        """ Returns all normal vectors of the hulls at the intersection point. """
        return [hull.normal * (-1 if self.invert_normal else 1) for hull in self.hulls]

    @property
    def valid(self) -> bool:
        return 0 <= self.time <= 1.0
    
    @property
    def hull(self) -> Optional[Segment]:
        if len(self.hulls) == 0:
            return None
        return self.hulls[0]
    

class Intersections2D(List[Intersection2D]):
    """ Collection of 2D intersections for an entity. """
    
    def __init__(self):
        super().__init__()
        self.time = 1.0
    
    def add(self, intersection: Intersection2D):
        """ Adds an intersection to the collection. """
        if not intersection.valid:
            return
        if intersection.time < self.time:
            self[:] = [intersection]
            self.time = intersection.time
        elif intersection.time == self.time and intersection.target is not None:
            self.append(intersection)
    
    def clear(self):
        """ Clears all intersections. """
        super().clear()
        self.time = 1.0
    
    def includes(self, entity: Entity) -> bool:
        """ Checks if the collection includes an intersection with the given entity. """
        return any(inter.target is entity for inter in self)
    
    def empty(self) -> bool:
        """ Checks if there are no intersections. """
        return len(self) == 0