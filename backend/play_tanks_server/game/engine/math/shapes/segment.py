from play_tanks_server.game.engine.math import Transform, Vec2
from play_tanks_server.game.engine.math.shapes import Shape, T


# Should be vector array
class Segment(Shape):

    def __init__(self, start: Vec2, end: Vec2):
        super().__init__([start, end])
        direction = self.end - self.start
        self.direction = direction.normalised()
        self.length = direction.magnitude()

    @property
    def start(self) -> Vec2:
        return self._vectors[0]
    
    @property
    def end(self) -> Vec2:
        return self._vectors[1]
    
    def transform_from_start(self) -> Transform:
        """ Returns a transform at the start of the segment. """
        return Transform(
            position=self.start.clone(),
            direction=self.direction     
        )
    
    def transform_from_end(self) -> Transform:
        """ Returns a transform at the end of the segment. """
        return Transform(
            position=self.end.clone(),
            direction=self.direction
        )

    def __eq__(self, other):
        if not isinstance(other, Segment):
            return False
        return (
            self.start == other.start and self.end == other.end or 
            self.start == other.end and self.end == other.start
        )

    def __hash__(self):
        """ 
        Orders the points to ensure that lines with the same start and end points 
        have the same hash. 
        """
        points = sorted((self.start, self.end), key=lambda p: [p[i] for i in range(len(p))])
        return hash((*points[0], *points[1]))

