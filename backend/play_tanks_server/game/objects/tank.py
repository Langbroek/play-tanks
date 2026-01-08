from typing import List

from play_tanks_server.game.engine.math import Vec2, Transform
from play_tanks_server.game.objects import DynamicEntity, Projectile
from play_tanks_server.game.models.stats import TankStats


class Tank(DynamicEntity[TankStats]):

    def __init__(self, stats: TankStats = TankStats(), **kwargs):
        super().__init__(stats=stats, **kwargs)
        self.ammo_cooldown_timer = -1
        self.cannon_rotation = 0.0  # In degrees
        self.cannon_direction = self.transform.direction.clone() # Initial cannon direction
        self.projectiles: List[Projectile] = []

    def is_cannon_on_cooldown(self) -> bool:
        """ Check if the cannon is on cooldown. """
        return 0 <= self.ammo_cooldown_timer < self.stats.ammo_cooldown

    def aim(self, target_position: Vec2, scalar: float = -1):
        """ Aim the tank's cannon/barrel towards a target position. """
        direction = (target_position - self.transform.position).normalised()
        self.cannon_direction = direction

    def fire(self):
        """ Fire a projectile if ammo is available. """
        if len(self.projectiles) >= self.stats.ammo_capacity:
            return  # No ammo available
        if self.is_cannon_on_cooldown():
            return  # Still in cooldown

        projectile = Projectile(
            stats=self.stats.projectile_stats,
            transform=Transform(
                position=self.transform.position,
                direction=self.cannon_direction
            )
        )
        self.projectiles.append(projectile)

    def update(self):
        """ Remove any destroyed projectiles before updating. """
        self.projectiles = [p for p in self.projectiles if not p.is_destroyed]
        if self.health <= 0 and not self.is_destroyed:
            self.destroy()
        if self.is_cannon_on_cooldown():
            self.ammo_cooldown_timer += 1
        else:
            self.ammo_cooldown_timer = -1

        for projectile in self.projectiles:
            projectile.update()

        return super().update()