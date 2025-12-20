from dataclasses import dataclass
from typing import Optional

from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.objects.collisions import HitBox, EmptyHitBox


@dataclass(frozen=True)
class EntityStats:
    """
    Base class for entity stats.
    """
    width: float = 0.0
    height: float = 0.0
    
    max_health: float = 100.0
    damage: float = 0.0

    def create_hit_box(self, anchor: Optional[Vec2] = None) -> HitBox:
        """ Create the hitbox for the entity based on its stats. Override in subclasses. """
        if self.width == 0.0 or self.height == 0.0:
            return EmptyHitBox()
        return HitBox(width=self.width, height=self.height, anchor=anchor)
    

@dataclass(frozen=True)
class StaticStats(EntityStats):
    """
    Stats for static entities.
    """
    height: float = 0.0


@dataclass(frozen=True)
class DynamicStats(EntityStats):
    """
    Stats for dynamic entities.
    """
    velocity: float = 0.0
    rotation_speed: float = 0.0

