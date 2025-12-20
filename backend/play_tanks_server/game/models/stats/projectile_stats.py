from dataclasses import dataclass

from play_tanks_server.game.models.stats import DynamicStats


@dataclass(frozen=True)
class ProjectileStats(DynamicStats):
    """
    Bullet stats.
    """
    width: float = 0.1
    height: float = 0.2
    max_health: float = 1.0
    damage: float = 1000
    velocity: float = 20
    rotation_speed: float = 0.0
    max_bounces: int = 3
    explosion_radius: float = 0.0
    explosion_damage: float = 0.0


