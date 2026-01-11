import threading

from typing import List
from typing_extensions import Self

from play_tanks_server.core.log import with_function_logger
from play_tanks_server.exceptions import GameAlreadyStartedException, with_exception_context

from play_tanks_server.game.engine import CollisionGridHeap
from play_tanks_server.game.engine.physics import engine as pe
from play_tanks_server.game.models.collisions import Intersections2D
from play_tanks_server.game.models.encoding import EncodedGameWorld
from play_tanks_server.game.objects import GameObject, Entity, Player, Projectile, Tank
from play_tanks_server.game.state import PlayerGameStates, GameMap
from play_tanks_server.game.state.actions import ACTION_TYPE as A, Action


class GameWorld(GameObject):

    def __init__(self, map: GameMap, max_players: int = 16):
        super().__init__()
        self.init_logger()  # Initialise logger after GameObject init
        self._lock = threading.Lock()
        self.max_players = max_players
        self.entities: List[Entity] = []

        self.players = PlayerGameStates(max_players)
        self.map = map

        self.game_time = 0.0
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
    def handle_player_action(self, player: Player, action: Action):
        """ Handle an action from a player. """
        state = self.players.players.get(player)
        if state is None:
            self.logger.warning(f"Received action from unknown player {player}.")
            return
        state.set_action(action)
    
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
        self.game_time += delta_time
        self._handle_tank_movement(delta_time)
        self._handle_entity_movement(delta_time)
        self._handle_tank_barrel_rotation(delta_time)
        self._handle_tank_shooting(delta_time)
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
            if action.vector.magnitude() > 0:
                state.set_action(action)  # Re-set action for continuous movement

    @with_function_logger(context="game_update")
    def _handle_entity_movement(self, delta_time: float):
        """ Handle projectile movement. """
        heap = CollisionGridHeap(cells_x=50, cells_y=50, delta_time=delta_time)
        # First add all aabb with movement to the heap
        for source in self.players.entities():
            heap.add_entity(source)
        # Add static map objects to the heap
        for wall in self.map.walls:
            heap.add_entity(wall, static=True)
        # Resolve movements
        while heap.has_events():
            event = heap.pop_event()
            source = event.entity
            if source.is_destroyed:
                continue
            # Move entity to collision point
            transform = event.transform
            if transform is not None:
                source.set_transform(transform)
                heap.update_event_time(event)
                heap.recompute_events(event, 'block')
            else:
                source.base_velocity()  # Reset to base velocity if no movement
            # Apply damage
            source_hit = False
            for intersection in event.intersections:
                intersection.target.apply_damage(source)
                source.apply_damage(intersection.target)  # Take damage from target.
                source_hit = True

            # Check if entity is alive otherwise stop
            if source.is_destroyed:
                continue
            # Check if entity has remaining movement time
            if 1 - event.time <= 0:
                continue
            # Recompute movement collision
            if source_hit and isinstance(source, Projectile):
                # Projectile should bounce on collision
                velocity = pe.calculate_bounce_velocity(source, event.intersections)
                source.set_velocity(velocity)
            elif source_hit and isinstance(source, Tank):
                # Tank should move in direction that is not stuck.
                velocity = pe.calculate_tank_slide(source, heap.blocked_intersections(event))
                source.set_velocity(velocity)

            # Update aabb
            heap.update_event_aabb(event)
            # Find earliest intersection.
            intersections = Intersections2D(1.0)
            # Only check for collisions if entity is moving
            if source.velocity.magnitude() > 0:
                for target_event in heap.non_blocked_grid_events(event):
                    intersection = pe.calculate_entity_intersection(source, target_event.entity, 
                                                                    source_time=event.time,
                                                                    target_time=target_event.time,
                                                                    scalar=delta_time)
                    
                    intersections.add(intersection)
            heap.update_event_intersections(event, intersections)
            # If we hit something, recompute all events that relied on this entity
            if source_hit:
                heap.recompute_events(event, 'hit')  
            heap.insert_event(event)


    @with_function_logger(context="game_update")
    def _handle_tank_barrel_rotation(self, delta_time: float):
        """ Handle tank barrel rotation actions. """
        for state in self.players.alive():
            action = state.pop_action(A.AIM)
            if action is None:
                continue
            state.tank.aim(action.vector)

    @with_function_logger(context="game_update") 
    def _handle_tank_shooting(self, delta_time: float):
        """ Handle tank shooting actions. """
        for state in self.players.alive():
            action = state.pop_action(A.SHOOT)
            if action is None:
                continue
            state.tank.fire()

    @with_function_logger(context="game_update")
    def _handle_entity_updates(self, delta_time: float):
        """ Handle entity updates. """
        for state in self.players:  # Iterate over all players, including destroyed ones
            state.tank.update()
            state.tank.clear_velocity()  # stop movement until user input.
            state.is_alive = not state.tank.is_destroyed

    @with_function_logger(context="game_encoding")
    def encode(self) -> EncodedGameWorld:
        """ Convert the game world state to serialisable game data. """
        return EncodedGameWorld(
            uid=self.uid,
            started=self.started,
            tick=self.game_tick,
            time=self.game_time,
            map_size=self.map.size,
            players=[state.player.encode() for state in self.players],
            entities=[wall.encode() for wall in self.map.walls] + [entity.encode() for entity in self.players.entities()]
        )