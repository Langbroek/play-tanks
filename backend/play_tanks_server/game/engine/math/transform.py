from typing import Union, Optional, overload
from typing_extensions import Self

from play_tanks_server.game.engine.math import Vec2, Vec2Array


class Transform:
    """ A class representing a 3D transformation including position and rotation. """
    def __init__(self, position: Optional[Vec2], direction: Optional[Vec2]):
        self.position = Vec2(0, 0) if position is None else position
        self.direction = (Vec2(0, 1) if direction is None else direction).normalised()
    
    def translated(self, vec: Vec2) -> Self:
        """ Translate the position by the given vector. """
        return Transform(self.position.translated(vec), self.direction)
    
    def translate(self, vec: Vec2):
        """ Translate the position by the given vector. """
        self.position.translate(vec)
    
    def rotated(self, vec: Vec2) -> Self:
        """ Rotate by the given vector. """
        return Transform(self.position, self.direction.rotated(vec))
    
    def rotate(self, vec: Vec2):
        """ Rotate by the given vector. """
        self.direction.rotate(vec)

    def with_position(self, position: Vec2) -> Self:
        """ Return a new Transform with the given position. """
        return Transform(position, self.direction)
    
    def with_direction(self, direction: Vec2) -> Self:
        """ Return a new Transform with the given direction. """
        return Transform(self.position, direction.normalised())
    
    def advance(self, scalar: float = 1.0):
        """ Advance the transform in the direction by the given scalar. """
        self.position.translate(self.direction * scalar)
    
    def advanced(self, scalar: float = 1.0) -> Self:
        """ Return a new Transform advanced in the direction by the given scalar. """
        return Transform(self.position.translated(self.direction * scalar), self.direction)
    
    @overload
    def apply(self, vector: Vec2) -> Vec2: ...
    @overload
    def apply(self, vectors: Vec2Array) -> Vec2Array: ...
    def apply(self, vector: Union[Vec2, Vec2Array]) -> Union[Vec2, Vec2Array]:
        """ Apply the transform to a point or array of points. """
        rotated = vector.rotated(self.direction.normalised())
        return rotated.translated(self.position)

    def __eq__(self, value):
        if not isinstance(value, Transform):
            return False
        return self.position == value.position and self.direction == value.direction