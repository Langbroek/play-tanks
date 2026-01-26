from typing import Optional, List, Generic
from typing_extensions import Self, TypeVar

from play_tanks_server.game.engine.math import Transform, Vec2
from play_tanks_server.game.engine.math.shapes import Segment, Rectangle
from play_tanks_server.game.models.encoding import EncodedEntity
from play_tanks_server.game.models.stats import EntityStats, DynamicStats, StaticStats
from play_tanks_server.game.objects import GameObject


S = TypeVar('S', bound=EntityStats, default=EntityStats)
DS = TypeVar('DS', bound=DynamicStats, default=DynamicStats)
SS = TypeVar('SS', bound=StaticStats, default=StaticStats)


class Entity(GameObject, Generic[S]):
    def __init__(self, 
                 local_pos: Optional[Vec2] = None,
                 transform: Optional[Transform] = None,
                 velocity: Optional[Vec2] = None,
                 stats: S = EntityStats(),
                 parent: Optional[GameObject] = None):
        super().__init__()
        self.stats = stats
        self.parent = parent
        self.is_destroyed = False
        self.is_spawned = False
        self.health = self.stats.max_health

        self.local_pos = Vec2(0.0, 0.0) if local_pos is None else local_pos
        self.local_hit_box = self.stats.create_hit_box()

        self.transform = Transform() if transform is None else transform
        self._velocity = Vec2(0.0, 0.0) if velocity is None else velocity
        self._direction = self._velocity.normalised()

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
        return self._direction
    
    @property
    def velocity(self) -> Vec2:
        return self._velocity
    
    def set_velocity(self, velocity: Vec2):
        """ Set the entity's velocity vector. """
        self._velocity = velocity
        self._direction = velocity.normalised()
    
    def clear_world_cache(self):
        """ Clear cached world coordinates. """
        self._world_hit_box = None
        self._world_pos = None

    def destroy(self):
        """ Mark the entity as destroyed. """
        self.is_destroyed = True

    def apply_damage(self, entity: Self):
        """ Apply damage to the entity. Override in subclasses if needed. """
        pass

    def update(self):
        """ Update the entity's state. Override in subclasses if needed. """
        self.is_spawned = True

    def encode(self):
        return EncodedEntity(
            uid=self.uid,
            type=self.__class__.__name__,
            x=self.position.x,
            y=self.position.y,
            width=self.hit_box.width,
            length=self.hit_box.length,
            height=self.hit_box.height,
            rotation=self.transform.direction.to_degrees(),
            dir_x=self.transform.direction.x,
            dir_y=self.transform.direction.y,
        )
    

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

    def clear_velocity(self):
        """ Clear the entity's velocity. """
        self._direction = Vec2(0.0, 0.0)
        self.base_velocity()

    def base_velocity(self):
        """ Reset the entity's velocity to """
        base_speed = self.stats.velocity
        direction = self.direction
        self.set_velocity(direction * base_speed)

    def set_position(self, position: Vec2):
        """ Set the entity's position. """
        self.transform = self.transform.with_position(position)
        self.clear_world_cache()
    
    def set_transform(self, transform: Transform):
        """ Set the entity's transform. """
        self.transform = transform
        self.clear_world_cache()

    def set_direction(self, direction: Vec2):
        """ Set the entity's direction and update velocity accordingly. """
        self._direction = direction.normalised()
        if self._direction.magnitude() > 0:
            self.set_transform(self.transform.with_direction(self._direction))
        self.base_velocity()

    def get_displacement(self, time: float, direction: Optional[Vec2] = None, scalar: float = 1.0) -> Vec2:
        """ Return a new entity advanced in the direction it is facing over time. """
        direction = self.direction if direction is None else direction.normalised()
        return direction * self.velocity.magnitude() * (time * scalar)
