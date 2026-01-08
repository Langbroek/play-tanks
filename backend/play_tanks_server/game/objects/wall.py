from typing import List

from play_tanks_server.game.engine.math import Vec2, Transform
from play_tanks_server.game.engine.math.shapes import Rectangle
from play_tanks_server.game.objects import StaticEntity
from play_tanks_server.game.models.stats import WallStats


class Wall(StaticEntity[WallStats]):

    def __init__(self, rectangle: Rectangle, height: float = 0.0):
        """
        Wall object in the game world.
        For now the rectangle is assumed in game world coordinates so will be converted to transform + local pos.
        """
        super().__init__(
            stats=WallStats(rectangle.width, rectangle.length, height),
            transform=Transform(rectangle.center())
        )
        
