from typing import List
from typing_extensions import Self

from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.engine.math.shapes import Shape, Segment


class Rectangle(Shape):
    """ 
    A rectangle defined by two corner points (x1, y1) and (x2, y2). 
    Initalisation is axis-aligned in 2D space and assume forward facing along positive y-axis.
    """

    def __init__(self, x1: float, y1: float, x2: float, y2: float, height: float = 0.0):
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        super().__init__([
            Vec2(x2, y2, height),  # front right
            Vec2(x1, y2, height),  # front left
            Vec2(x1, y1, height),  # back left
            Vec2(x2, y1, height),  # back right
        ])

    @property
    def height(self) -> float:
        return self._vectors[0].z
    
    @property
    def width(self) -> float:
        return self.front().length
    
    @property
    def length(self) -> float:
        return self.right().length

    @property
    def front_left(self) -> Vec2:
        return self._vectors[1]
    
    @property
    def front_right(self) -> Vec2:
        return self._vectors[0]
    
    @property
    def back_right(self) -> Vec2:
        return self._vectors[3]
    
    @property
    def back_left(self) -> Vec2:
        return self._vectors[2]
        
    @property
    def x1(self) -> float:
        return self.back_left.x
    
    @property
    def y1(self) -> float:
        return self.back_left.y
    
    @property
    def x2(self) -> float:
        return self.front_right.x
    
    @property
    def y2(self) -> float:
        return self.front_right.y
    
    def center(self) -> Vec2:
        """ Returns the center point of the rectangle. """
        return self.front_left + ((self.back_right - self.front_left) / 2)
    
    # Want to go ccw for normals.
    def front(self) -> Segment:
        return Segment(self.front_right, self.front_left)
    
    def left(self) -> Segment:
        return Segment(self.front_left, self.back_left)
    
    def back(self) -> Segment:
        return Segment(self.back_left, self.back_right)

    def right(self) -> Segment:
        return Segment(self.back_right, self.front_right)
    
    def hulls(self) -> List[Segment]:
        """ Returns the four edges of the rectangle as segments. """
        return [self.front(), self.left(), self.back(), self.right()]
    
    def aabb(self) -> Self:
        """ Returns the axis-aligned bounding box of the rectangle (itself). """
        x_min, y_min = self._data[:, 0:2].min(axis=0)
        x_max, y_max = self._data[:, 0:2].max(axis=0)
        return Rectangle(x_min, y_max, x_max, y_min)  # Note: y_max is top, y_min is bottom
    
    def radius(self) -> float:
        """ Returns the radius of the rectangle (half the diagonal). """
        width = self.width
        length = self.length
        diagonal = (width ** 2 + length ** 2) ** 0.5
        return diagonal / 2

    def expand(self, size: Vec2):
        """ Expands the aabb by the given size based on signs. """
        if size.x > 0:
            self._data[1:3, 0] += size.x  # Top left x
        else:
            self._data[0:4:3, 0] += size.x  # Bottom right x
        if size.y > 0:
            self._data[0:2, 1] += size.y  # Bottom right y
        else:
            self._data[2:4, 1] += size.y  # Top left y
    
    def __str__(self):
        return f"Rectangle(x1: {self.x1}, y1: {self.y1}, x2: {self.x2}, y2: {self.y2})"

    def __repr__(self):
        return self.__str__()