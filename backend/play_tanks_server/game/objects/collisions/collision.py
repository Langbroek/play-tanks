

class Collision:
    """
    Base class for describing collisions.
    """
    def __init__(self, ignore_projectile: bool = False):
        super().__init__()
        self.ignore_projectile = ignore_projectile