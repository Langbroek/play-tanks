from dataclasses import dataclass, field

from play_tanks_server.game.models.stats import DynamicStats, ProjectileStats


@dataclass(frozen=True)
class TankStats(DynamicStats):
    """
      Tank stats.
    """
    width: float = 50.0
    length: float = 50.0
    max_health: float = 100.0

    velocity: float = 200.0
    rotation_speed: float = 0.0
    armour: float = 0.0

    ammo_capacity: int = 5
    ammo_cooldown: int = 5  # in seconds.

    projectile_stats: ProjectileStats = field(default_factory=ProjectileStats)