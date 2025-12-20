
from play_tanks_server.models.stats import ProjectileStats
from play_tanks_server.game.objects import Entity, StaticEntity, DynamicEntity



class Projectile(DynamicEntity):
    
    def __init__(self, stats: ProjectileStats, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = stats
        self.bounce_count = 0

    def can_bounce(self) -> bool:
        """ Check if the projectile can bounce again. """
        return self.bounce_count < self.stats.bounce_count

    def apply_damage(self, entity: Entity):
        """ Apply damage to the projectile. Destroys projectile. """
        if isinstance(entity, StaticEntity):
            self.bounce_count += 1
            if not self.can_bounce():
                self.destroy()
        elif isinstance(entity, DynamicEntity):
            self.destroy()
