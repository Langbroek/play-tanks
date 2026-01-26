from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.models.stats import ProjectileStats
from play_tanks_server.game.objects import Entity, StaticEntity, DynamicEntity



class Projectile(DynamicEntity[ProjectileStats]):
    
    def __init__(self, stats: ProjectileStats, direction: Vec2, *args, **kwargs):
        super().__init__(*args, stats=stats, **kwargs)
        self.bounce_count = 0
        self._direction = direction.normalised()
        self.base_velocity()

    def can_bounce(self) -> bool:
        """ Check if the projectile can bounce again. """
        return self.bounce_count < self.stats.max_bounces

    def apply_damage(self, entity: Entity):
        """ Apply damage to the projectile. Destroys projectile. """
        if isinstance(entity, StaticEntity):
            self.bounce_count += 1
            if not self.can_bounce():
                self.destroy()
        elif isinstance(entity, DynamicEntity):
            return  # for now
            self.destroy()

    def set_velocity(self, velocity):
        super().set_velocity(velocity)
        self.transform = self.transform.with_direction(self._direction)