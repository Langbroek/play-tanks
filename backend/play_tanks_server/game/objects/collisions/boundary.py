
from play_tanks_server.game.objects.collisions import Collision
from play_tanks_server.game.engine.math import Vector2
from play_tanks_server.game.engine.math.shapes import Segment


class BoundaryLine(Collision):

    def __init__(self, start: Vector2, end: Vector2):
        self.line = Segment(start, end)