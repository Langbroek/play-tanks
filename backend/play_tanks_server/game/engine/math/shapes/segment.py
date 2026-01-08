from play_tanks_server.game.engine.math import Transform, Vec2, Vec2Array


class Segment(Vec2Array):

    def __init__(self, start: Vec2, end: Vec2):
        super().__init__([start, end])
        self.displacement = self.end - self.start
        self.direction = self.displacement.normalised()
        self.normal = Vec2(self.direction.y, -self.direction.x)
        self.opposite_normal = self.normal * -1
        self.length = self.displacement.magnitude()

    @property
    def start(self) -> Vec2:
        return self._vectors[0]
    
    @property
    def end(self) -> Vec2:
        return self._vectors[1]

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

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"Segment(Start: {self.start}, End: {self.end})"