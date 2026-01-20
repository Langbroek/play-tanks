import random

from typing import List, Optional

from play_tanks_server.game.engine.physics import engine as pe
from play_tanks_server.game.engine.algorithm import WaypointNetwork
from play_tanks_server.game.engine.math import Transform, Vec2, Waypoint
from play_tanks_server.game.engine.math.shapes import Segment
from play_tanks_server.game.objects import GameObject, Tank


class Computer:

    def __init__(self, mode: str, owner: GameObject, threshold: float = 2.4, soft_cap: int = 6,
                 min_prob: float = 0.05, max_prob: float = 0.6):
        self._initialised = False
        self.mode = mode
        self.owner = owner
        self.threshold = threshold
        self.soft_cap = soft_cap
        self.min_prob = min_prob
        self.max_prob = max_prob

        self.last_waypoint: Optional[Waypoint] = None
        self.target_waypoint: Optional[Waypoint] = None
        self.target_tank: Optional[Tank] = None
        self.target_paths: List[Waypoint] = []

    def target_direction(self) -> Vec2:
        """ Returns the target velocity vector towards the current waypoint. """
        if self.target_waypoint is None or self.tank is None:
            return Vec2(0.0, 0.0)
        return (self.target_waypoint.position - self.tank.position).normalised()

    def initialise(self, tank: Tank, waypoints: WaypointNetwork):
        """ Initialise the computer's waypoint network. """
        if self._initialised:
            return
        self.tank = tank
        self.waypoints = waypoints
        self._initialised = True

    def update(self, targets: List[Tank]):
        """ Update the computer's state based on targets. """
        if not self._initialised:
            raise RuntimeError(f"Computer for {self.owner} has not been initialised.")
        if self.tank.is_destroyed:
            return
        
        if self._is_moving_to_target():
            return  # Still moving towards target
        self.target_waypoint = None
        
        if not self._select_new_target(targets):
            self._compute_resets()
        
        if self._can_compute_new_path():
            self._update_path_to_target()
            self._update_waypoint_to_follow()

    def _is_moving_to_target(self) -> bool:
        if self.target_waypoint is None:
            return False
        return not pe.vector_in_proximity(self.tank.position, self.target_waypoint.position, 
                                          self.threshold)
      
    def _can_compute_new_path(self) -> bool:
        return self.target_tank is not None and self.target_waypoint is None
    
    def _should_change_target(self) -> bool:
        """ Determine if the AI should change its target tank. """
        if self.target_tank is None or len(self.target_paths) == 0 or self.target_tank.is_destroyed:
            return True
        t = min(len(self.target_paths), self.soft_cap)
        switch_prob = self.min_prob + (self.max_prob - self.min_prob) * t
        return random.random() < switch_prob
    
    def _select_new_target(self, targets: List[Tank]) -> bool:
        """ 
        Check if new targets are needed and select them. Returns true if a new target was selected.
        """
        if self._should_change_target():
            new_tank = self.target_tank if len(targets) == 0 else random.choice(targets)
        else:
            new_tank = self.target_tank
        updated = new_tank != self.target_tank
        self.target_tank = new_tank
        return updated
            
    def _compute_resets(self):
        """ Calculate if the path needs to be recomputed. """
        if self.target_tank is None or self.target_tank.is_destroyed or len(self.target_paths) == 0:
            return self._reset()
        t = min(len(self.target_paths), self.soft_cap) / self.soft_cap
        recompute_prob = .2 - .2 * t
        if random.random() < recompute_prob:
            self.last_waypoint = self.target_waypoint
            self.target_waypoint = None
            self.target_paths = []

    def _update_path_to_target(self):
        """ Update the path to the target tank. """
        if self.last_waypoint is None:
            source_wp = random.choice(self.waypoints.get_line_of_sight_waypoints(self.tank.position))
        else:
            source_wp = self.last_waypoint
            self.last_waypoint = None
        target_wps = self.waypoints.get_line_of_sight_waypoints(self.target_tank.position)
        paths = self.waypoints.a_star_path_to_any_targets(source_wp, target_wps)
        self.target_paths = paths

    def _update_waypoint_to_follow(self):
        """ Update the next waypoint to follow along the path. """
        if len(self.target_paths) == 0:
            return self._reset()
        self.target_waypoint = self.target_paths.pop(0)
    
    def _reset(self): 
        self.last_waypoint = None
        self.target_waypoint = None
        self.target_tank = None
        self.target_paths = []