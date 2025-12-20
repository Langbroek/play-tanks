from dataclasses import dataclass, field

from play_tanks_server.game.models.stats import ProjectileStats


@dataclass(frozen=True)
class TankStats:
    """
      Tank stats.
    """
    width: 10.0
    height: 10.0
    max_health: float = 100.0

    velocity: float = 10.0
    rotation_speed: float = 0.0
    armour: float = 0.0

    ammo_capacity: int = 5
    ammo_cooldown: int = 30  # In ticks

    projectile_stats: ProjectileStats = field(default_factory=ProjectileStats)