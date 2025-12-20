from typing import Optional, List, Generic
from typing_extensions import Self, TypeVar

from play_tanks_server.game.engine.math import Transform, Vec2
from play_tanks_server.game.engine.math.shapes import Segment, Rectangle
from play_tanks_server.game.models.stats import EntityStats, DynamicStats, StaticStats
from play_tanks_server.game.objects import GameObject


S = TypeVar('S', bound=EntityStats, default=EntityStats)
DS = TypeVar('DS', bound=DynamicStats, default=DynamicStats)
SS = TypeVar('SS', bound=StaticStats, default=StaticStats)


class Entity(GameObject, Generic[S]):
    def __init__(self, 
                 local_pos: Optional[Vec2] = None,
                 transform: Optional[Transform] = None,
                 stats: S = EntityStats()):
        super().__init__()
        self.stats = stats
        self.local_pos = Vec2(0.0, 0.0) if local_pos is None else local_pos
        self.local_hit_box = self.stats.create_hit_box()
        self.transform = Transform() if transform is None else transform

        self.is_destroyed = False
        self.is_spawned = True
        self.health = self.stats.max_health

        self._world_hit_box: Optional[Rectangle] = None
        self._world_pos: Optional[Vec2] = None

    @property
    def hit_box(self) -> Rectangle:
        """ Returns the entity's hitbox in world coordinates. """
        if self._world_hit_box is None:
            self._world_hit_box = self.local_hit_box.world(self.transform)
        return self._world_hit_box
    
    @property
    def position(self) -> Vec2:
        """ Returns the entity's position in world coordinates. """
        if self._world_pos is None:
            self._world_pos = self.transform.apply(self.local_pos)
        return self._world_pos
    
    @property
    def direction(self) -> Vec2:
        """ Returns the entity's direction vector. """
        return self.transform.direction
    
    def clear_world_cache(self):
        """ Clear cached world coordinates. """
        self._world_hit_box = None
        self._world_pos = None

    def max_health(self) -> float:
        """ Returns the maximum health of the entity. Override in subclasses if needed. """
        return 100.0

    def destroy(self):
        """ Mark the entity as destroyed. """
        self.is_destroyed = True

    def apply_damage(self, entity: Self):
        """ Apply damage to the entity. Override in subclasses if needed. """
        pass

    def collides(self, entity: Self) -> bool:
        """ Check if this entity collides with another entity. """
        return False

    def update(self):
        """ Update the entity's state. Override in subclasses if needed. """
        self.is_spawned = False


class StaticEntity(Entity[SS]):
    """
    An entity that does not move.
    """
    def __init__(self, stats: SS = StaticStats(), **kwargs):
        super().__init__(stats=stats, **kwargs)


class DynamicEntity(Entity[DS]):
    """
    An entity that can move.
    """
    def __init__(self, stats: DS = DynamicStats(), **kwargs):
        super().__init__(stats=stats, **kwargs)
        self.prev_transforms: List[Transform] = []

    def get_velocity(self) -> float:
        """ Get the entity's current velocity. Override in subclasses if needed. """
        return self.stats.velocity

    def set_transform(self, transform: Transform):
        """ Set the entity's transform. """
        self.prev_transforms.append(self.transform)  # Save
        self.transform = transform
        self.clear_world_cache()

    def set_position(self, position: Vec2):
        """ Set the entity's position. without changing rotation. """
        self.set_transform(self.transform.with_position(position))

    def set_direction(self, direction: Vec2):
        """ Set the entity's direction without changing position. """
        self.set_transform(self.transform.with_direction(direction))
        
    def advance(self, scalar: float, direction: Optional[Vec2] = None):
        """ Move the entity forward in the direction it is facing. """
        segment = self.segment(scalar, direction)
        self.set_transform(segment.transform_from_end())

    def segment(self, scalar: float, direction: Optional[Vec2] = None) -> Segment:
        """ 
        Return the segment representing the entity's movement over the given 
        scalar and direction if provided. 
        """
        start_pos = self.position.clone()
        direction = (self.direction if direction is None else direction).normalised()
        end_pos = start_pos + (direction * scalar * self.get_velocity())
        return Segment(start_pos, end_pos)

    def update(self):
        """ Update the entity's state. Override in subclasses if needed. """
        self.prev_transforms.clear()  # Clear previous transforms
        return super().update()