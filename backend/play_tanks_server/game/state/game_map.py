import numpy as np
import random

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
        self.cannon_height = cannon_height
        self.offset = Vec2(-self._map.shape[1] / 2, -self._map.shape[0] / 2)
        self.scale = Vec2(scale, -scale)  # Invert y-axis
        self.aabb = Rectangle(self.offset.x, self.offset.y, -self.offset.x, -self.offset.y) * self.scale
        self.size = (int(self._map.shape[1] * scale), int(self._map.shape[0] * scale))
        self._initialise_collisions()
        self.network = WaypointNetwork((((scale ** 2) * 2) ** .5) / 2, self.hulls(), self.corners)
    
    def hulls(self) -> List[Segment]:
        """ Returns all wall hulls for collision detection. """
        return [hull for wall in self.walls for hull in wall.hit_box.hulls()]
    
    def get_spawn_points(self, count: int) -> List[Vec2]:
        """ 
        Returns a list of valid spawn points on the map. 
        Creates a rectangle offset from the full map size. Then divides the perimeter
        into equal segments based on count. Then tries to find a valid spawn point on each segment.
        """
        # Pick a start point randomly for algorithm.
        spawnpoints = pe.generate_random_map_points(self._map, min(self._map.shape) * .2, 12)
        grid_offset = .5
        return [
            (Vec2(point[0], point[1]) + grid_offset + self.offset) * self.scale
            for point in spawnpoints[:count]
        ]

    def _initialise_collisions(self):
        """
        Initialise the collision hitboxes from the map array.
        center of map is 0, 0
        """
        self.walls.clear()

        low_obstacles = (self._map > 0) & (self._map <= self.cannon_height)
        high_obstacles = self._map > self.cannon_height
        for obstacle_array, low_flag in [(low_obstacles, True), (high_obstacles, False)]:
            contours = array_to_rectangles(obstacle_array)
            self.walls.extend([Wall(rect.translated(self.offset) * self.scale, low_flag) 
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