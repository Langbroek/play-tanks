import numpy as np

from typing import List, Tuple

from play_tanks_server.game.engine.algorithm import WaypointNetwork
from play_tanks_server.game.engine.algorithm.clusters import array_to_rectangles
from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.engine.math.shapes import Rectangle, Segment
from play_tanks_server.game.engine.physics import engine as pe
from play_tanks_server.game.objects import Wall


class GameMap:
    """
    This is a game map which can be created from a numpy array of floats which then converts
    into a list of hitboxes for collision detection.
    """
    def __init__(self, input_array: np.ndarray, scale: float = 7.7, cannon_height: float = 0.5):
        self.walls: List[Wall] = []
        self._map = input_array
        self._scale = scale
        self.cannon_height = cannon_height
        self._initialise_collisions()
        self.network = WaypointNetwork((((self._scale ** 2) * 2) ** .5) / 2, self.hulls(), self.corners)

    @property
    def size(self) -> Tuple[int, int]:
        """ Return the size of the map in pixels. """
        return int(self._map.shape[1] * self._scale), int(self._map.shape[0] * self._scale)
    
    def hulls(self) -> List[Segment]:
        """ Returns all wall hulls for collision detection. """
        return [hull for wall in self.walls for hull in wall.hit_box.hulls()]

    def _initialise_collisions(self):
        """
        Initialise the collision hitboxes from the map array.
        center of map is 0, 0
        """
        self.walls.clear()
        offset = Vec2(-self._map.shape[1] / 2, -self._map.shape[0] / 2)
        scale = Vec2(self._scale, -self._scale)  # Invert y-axis
        self.aabb = Rectangle(offset.x, offset.y, -offset.x, -offset.y) * scale

        low_obstacles = (self._map > 0) & (self._map <= self.cannon_height)
        high_obstacles = self._map > self.cannon_height
        for obstacle_array, low_flag in [(low_obstacles, True), (high_obstacles, False)]:
            contours = array_to_rectangles(obstacle_array)
            self.walls.extend([Wall(rect.translated(offset) * scale, low_flag) 
                                    for rects in contours.values() for rect in rects])
            
        self.corners = pe.calculate_map_concave_corners(self.walls, self.aabb)


def main():
    map = GameMap(np.array([
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 1, 1, 1, 1, 0, 0, 1],
        [1, 0, 0, 1, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, .2, .2, 0, 0, 0, 1],
        [1, 0, 1, 0, .2, .2, 0, 0, 0, 1],
        [1, 0, 1, 0, 0, 0, .2, 0, 0, 1],
        [1, 0, 1, 1, 1, .2, .2, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]), scale=50)



if __name__ == '__main__':
    main()