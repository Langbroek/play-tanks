import itertools
import threading

from typing import List
from typing_extensions import Self

from play_tanks_server.core.log import with_function_logger
from play_tanks_server.exceptions import GameAlreadyStartedException, with_exception_context

from play_tanks_server.game.engine.physics import engine as pe
from play_tanks_server.game.objects import GameObject, Entity, Player, Projectile
from play_tanks_server.game.state import PlayerGameStates, GameMap, CollisionHeap
from play_tanks_server.game.state.actions import ACTION_TYPE as A


MAX_COLLISION_ITERATIONS = 5


class GameWorld(GameObject):

    def __init__(self, max_players: int = 16):
        super().__init__()
        self.init_logger()  # Initialise logger after GameObject init
        self._lock = threading.Lock()
        self.max_players = max_players
        self.entities: List[Entity] = []

        self.players = PlayerGameStates(max_players)
        self.map = GameMap()

        self.game_tick = -1
        
    @property
    def started(self) -> bool:
        """ Check if the game has started. """
        return self.game_tick >= 0
    
    # GameWorld decorators
    
    def with_world_lock(func):
        """ Decorator to ensure thread-safe access to the game world. """
        def wrapper(self: Self, *args, **kwargs):
            with self._lock:
                return func(self, *args, **kwargs)
        return wrapper

    # Game functions
    
    @with_world_lock
    @with_exception_context
    @with_function_logger
    def join(self, player: Player):
        """ Add a player to the game world. """
        if self.started:
            raise GameAlreadyStartedException(f"{player} tried to join a started game.")
        self.players.add(player)

    @with_world_lock
    @with_exception_context
    @with_function_logger
    def leave(self, player: Player):
        """ Remove a player from the game world. """
        self.players.remove(player)

    @with_world_lock
    @with_function_logger
    def handle_player_action(self, player: Player, action):
        """ Handle an action from a player. """
        return
    
    @with_world_lock
    @with_function_logger(context="game_update", log_every_n=60)
    def update(self, delta_time: float):
        """ 
        Update the game world state. 
        Order of action handling:
        MOVEMENT
        COLLISIONS
        PROJECTILES SPAWN
        PROJECTILES MOVEMENT
        DAMAGE CALCULATION
        ENTITY UPDATES
        """
        self.game_tick += 1
        self._handle_tank_movement(delta_time)
        self._handle_tank_on_map_collisions(delta_time)
        self._handle_tanks_collisions(delta_time)
        self._handle_tank_barrel_rotation(delta_time)
        self._handle_tank_shooting(delta_time)
        self._handle_tank_projectile_movement(delta_time)
        self._handle_tank_projectile_map_collisions(delta_time)
        self._handle_tank_projectile_damage(delta_time)
        self._handle_entity_updates(delta_time)
        # self._handle_disconnections()

    # Private functions assume the world lock is held.

    @with_function_logger(context="game_update")
    def _handle_tank_movement(self, delta_time: float):
        """ Handle tank movement actions. """
        for state in self.players.alive():
            action = state.pop_action(A.MOVE)
            if action is None:
                continue
            state.tank.set_direction(action.vector)
            state.tank.advance(delta_time)

    @with_function_logger(context="game_update")
    def _handle_tank_on_map_collisions(self, delta_time: float):
        """ Handle movement collisions between entities. """
        # First move all from illlegal map positions
        for _ in range(MAX_COLLISION_ITERATIONS):
            any_collision = False
            for state in self.players.alive():
                transform, hit = pe.resolve_static_tank_collision(state.tank, self.map)
                if not hit:
                    continue
                any_collision = True
                # Update tank position without changing rotation
                state.tank.set_position(transform.position)
            if not any_collision:
                break

    @with_function_logger(context="game_update")
    def _handle_tanks_collisions(self, delta_time: float):
        """ Handle movement collisions between entities. """
        for _ in range(MAX_COLLISION_ITERATIONS):
            any_collision = False
            for state_a, state_b in itertools.combinations(self.players.alive(), 2):
                tfm_a, tfm_b, hit = pe.resolve_tanks_collision(state_a.tank, state_b.tank, self.map)
                if not hit:
                    continue
                any_collision = True
                state_a.tank.set_position(tfm_a.position)
                state_b.tank.set_position(tfm_b.position)
            if not any_collision:
                break

    @with_function_logger(context="game_update")
    def _handle_tank_barrel_rotation(self, delta_time: float):
        """ Handle tank barrel rotation actions. """
        for state in self.players.alive():
            action = state.pop_action(A.ROTATE)
            if action is None:
                continue
            state.tank.aim(action.vector, delta_time)

    @with_function_logger(context="game_update") 
    def _handle_tank_shooting(self, delta_time: float):
        """ Handle tank shooting actions. """
        for state in self.players.alive():
            action = state.pop_action(A.SHOOT)
            if action is None:
                continue
            state.tank.fire()

    @with_function_logger(context="game_update")
    def _handle_tank_projectile_collisions(self, delta_time: float):
        """ Handle tank damage calculation from projectiles. """
        collisions = CollisionHeap()
        for projectile in self.players.projectiles():
            collision = pe.resolve_projectile_collision(projectile, self.players.entities(), 
                                                        self.map, delta_time)
            collisions.add(collision)
        while not collisions.is_empty():
            event = collisions.pop()
            projectile: Projectile = event.source

            if projectile.is_destroyed:
                continue
            
            # Move projectile to collision point
            projectile.advance(event.distance * delta_time)

            # Only apply damage if the event doesnt require a new collision computation
            if not event.recompute:
                # Apply damage
                target = event.target
                if not target.is_destroyed:
                    target.apply_damage(projectile)
                    projectile.apply_damage(target)  # Take damage from target.
                    if projectile.is_destroyed:
                        continue  # Stop the projectile if destroyed
                
                if isinstance(target, GameMap):
                    # Rotate the projectile direction based on collision normal
                    direction = pe.calculate_bounce_direction(projectile, event.collision_normal)
                    projectile.set_direction(direction)
                    collisions.recompute_target(projectile)
            
            if 1 - event.distance <= 0:
                continue  # No time left to process further collisions this tick

            collision = pe.resolve_projectile_collision(projectile, self.players.entities(), 
                                                        self.map, (1 - event.distance) * delta_time)
            collisions.add(collision)

    @with_function_logger(context="game_update")
    def _handle_entity_updates(self, delta_time: float):
        """ Handle entity updates. """
        for state in self.players:  # Iterate over all players, including destroyed ones
            state.tank.update()
            state.is_alive = not state.tank.is_destroyed


    

