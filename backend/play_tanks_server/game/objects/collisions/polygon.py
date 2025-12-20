from typing import List

from play_tanks_server.game.objects.collisions import Collision
from play_tanks_server.game.engine.math.shapes import Segment


class PolygonCollision(Collision):
    """ A polygonal hitbox class for collision detection. """
    def __init__(self, contour: List[Segment], low_flag: bool = False):
        self.contour = contour
        self.low_flag = low_flag