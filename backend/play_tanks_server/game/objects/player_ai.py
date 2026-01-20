
from typing import List

from play_tanks_server.game.engine.algorithm import WaypointNetwork
from play_tanks_server.game.engine.computer import Computer
from play_tanks_server.game.objects import Player, Tank


class PlayerAI(Player):

    def __init__(self, name: str, mode: str = 'easy', **kwargs):
        super().__init__(name, **kwargs)
        self.computer = Computer(mode, self)

    def encode(self):
        encoded = super().encode()
        encoded.data.update({
            'mode': self.computer.mode,
            'waypoints': [
                (wp.name, wp.position) for wp in self.computer.waypoints.waypoint_grid.values()
            ],
            'paths': [
                (path.source.name, path.target.name, path.cost) for path in self.computer.waypoints.waypoint_map.values()
            ],
            'targets': [
                wp.name for wp in self.computer.target_paths
            ]
        })
        return encoded