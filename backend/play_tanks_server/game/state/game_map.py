import numpy as np

from typing import List

from play_tanks_server.game.engine.math import Vec2I, Vec2F
from play_tanks_server.game.engine.math.shapes import Segment
from play_tanks_server.game.engine.math.clusters import array_to_rectangles
from play_tanks_server.game.objects.collisions import HitBox, BoundaryLine


class GameMap:
    """
    This is a game map which can be created from a numpy array of floats which then converts
    into a list of hitboxes for collision detection.
    """
    def __init__(self, input_array: np.ndarray, scale: float = 7.7, cannon_height: float = 0.5):
        self.collisions = []
        self._map = input_array
        self._scale = scale
        self.cannon_height = cannon_height

        self._initialise_collisions()

    @property
    def size(self) -> Vec2I:
        """ Return the size of the map in pixels. """
        return Vec2I(int(self._map.shape[1] * self._scale), int(self._map.shape[0] * self._scale))

    def _to_map_coords(self, coord: Vec2I) -> Vec2F:
        """ 
          Convert array index to map coordinate, this also offsets the index
          so that the center of the map is at (0, 0).
          for example, index 0 in a 10 width map becomes -5 * scale
        """
        return Vec2F(
            (coord[0] - self._map.shape[1] / 2) * self._scale,
            (coord[1] - self._map.shape[0] / 2) * self._scale
        )
    
    def _line_to_map_coords(self, line: Segment) -> Segment:
        """ Convert a line from array index coordinates to map coordinates. """
        return Segment(
            self._to_map_coords(line.start),
            self._to_map_coords(line.end)
        )

    def _initialise_collisions(self):
        """
        Initialise the collision hitboxes from the map array.
        center of map is 0, 0
        """
        self.collisions.clear()
        top_left = self._to_map_coords(Vec2I(0, 0))
        bottom_right = self._to_map_coords(Vec2I(self._map.shape[1], self._map.shape[0]))
        top_right = Vec2F(bottom_right[0], top_left[1])
        bottom_left = Vec2F(top_left[0], bottom_right[1])

        # Hardcode boundary lines around the map
        self.collisions.extend([
            BoundaryLine(top_left, top_right), # Top
            BoundaryLine(top_right, bottom_right), # Right
            BoundaryLine(bottom_left, bottom_right), # Bottom
            BoundaryLine(top_left, bottom_left)  # Left
        ])

        low_countours = array_to_rectangles((self._map > 0) & (self._map <= self.cannon_height))
        self.collisions.extend([HitBox.from_corners(
                top_left=self._to_map_coords(rect.top_left),
                bottom_right=self._to_map_coords(rect.bottom_right),
                ignore_projectile=True,
            ) for rects in low_countours.values() for rect in rects])
        
        high_contours = array_to_rectangles(self._map > self.cannon_height)
        self.collisions.extend([HitBox.from_corners(
                top_left=self._to_map_coords(rect.top_left),
                bottom_right=self._to_map_coords(rect.bottom_right)
            ) for rects in high_contours.values() for rect in rects])
        

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

    width, height = map.size
    print(f"Map size: {width} x {height}")
    import cv2

    array = np.full((height, width, 3), (255, 255, 255), dtype=np.uint8)
    for collision in map.collisions:
        if not isinstance(collision, HitBox):
            continue
        start = collision.x1, collision.y1
        end = collision.x2, collision.y2
        colour = (0, 255, 0) if collision.low_flag else (255, 0, 0)
        border_colour = (25, 200, 25) if collision.low_flag else (200, 25, 25)

        cv2.rectangle(array, (int(start[0] + width / 2), int(start[1] + height / 2)),
                     (int(end[0] + width / 2), int(end[1] + height / 2)), colour, -1)
        cv2.rectangle(array, (int(start[0] + width / 2), int(start[1] + height / 2)),
                        (int(end[0] + width / 2), int(end[1] + height / 2)), border_colour, 2)

    from PIL import Image
    img = Image.fromarray(array, 'RGB')
    img.show()




if __name__ == '__main__':
    main()