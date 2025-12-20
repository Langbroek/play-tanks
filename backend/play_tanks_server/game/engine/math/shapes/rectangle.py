from play_tanks_server.game.engine.math import Vec2, Vec2Array
from play_tanks_server.game.engine.math.shapes import Shape


class Rectangle(Shape):
    """ A rectangle defined by its top-left and bottom-right corners. """

    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        super().__init__([
            Vec2(x1, y1),  # Top left
            Vec2(x2, y1),  # Top right
            Vec2(x2, y2),  # Bottom right
            Vec2(x1, y2),  # Bottom left
        ])

    @property
    def top_left(self) -> Vec2:
        return self._vectors[0]
    
    @property
    def top_right(self) -> Vec2:
        return self._vectors[1]
    
    @property
    def bottom_right(self) -> Vec2:
        return self._vectors[2]
    
    @property
    def bottom_left(self) -> Vec2:
        return self._vectors[3]
        
    @property
    def x1(self) -> float:
        return self.top_left.x
    
    @property
    def y1(self) -> float:
        return self.top_left.y
    
    @property
    def x2(self) -> float:
        return self.bottom_right.x
    
    @property
    def y2(self) -> float:
        return self.bottom_right.y
    
    def __str__(self):
        return f"Rectangle(x1: {self.x1}, y1: {self.y1}, x2: {self.x2}, y2: {self.y2})"
