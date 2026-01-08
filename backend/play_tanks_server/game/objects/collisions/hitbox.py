from typing import Optional

from play_tanks_server.game.engine.math import Transform, Vec2
from play_tanks_server.game.engine.math.shapes import Rectangle
from play_tanks_server.game.objects.collisions import Collision


class HitBox(Collision):
    """ A simple hitbox class for collision detection. """
    def __init__(self, width: float, length: float, anchor: Optional[Vec2] = None, height: float = 0.0, **kwargs):
        """ Initialise a HitBox from corner points or coordinates. """
        super().__init__(**kwargs)
        x1, y1, x2, y2 = width / 2, -length / 2, -width / 2, length / 2

        if anchor is None:
            anchor = Vec2(0, 0)

        self.local = Rectangle(x1 + anchor.x, y1 + anchor.y, x2 + anchor.x, y2 + anchor.y, height)
        self.height = length
        self.width = width

    def world(self, transform: Transform) -> Rectangle:
        """ Returns the hitbox in world coordinates given a transform. """
        return transform.apply(self.local)
    

class EmptyHitBox(HitBox):
    """ An empty hitbox that represents no collision area. """
    def __init__(self):
        super().__init__(0, 0, Vec2(0, 0))

    def world(self, transform: Transform) -> Rectangle:
        """ Returns an empty rectangle in world coordinates. """
        return Rectangle(0, 0, 0, 0)