from typing import Tuple

from play_tanks_server.game.engine.math import Vec2


class Waypoint:
    def __init__(self, position: Vec2, index: int = -1):
        self.name = f"WP_{index}" if index >= 0 else "WP"
        self.position = position

    def __hash__(self):
        return self.name.__hash__()
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Waypoint):
            return False
        return self.name == other.name

    def to_cell_coords(self) -> Tuple[int, int]:
        return (int(self.position.x), int(self.position.y))