import threading

from typing import List
from typing_extensions import Self

from play_tanks_server.core.log import with_function_logger
from play_tanks_server.exceptions import GameAlreadyStartedException, with_exception_context

from play_tanks_server.game.engine.collisions import Intersections2D, CollisionGridHeap
from play_tanks_server.game.engine.physics import engine as pe
from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.models.encoding import EncodedGameWorld
from play_tanks_server.game.objects import GameObject, Entity, Player, Projectile, Tank, PlayerAI
from play_tanks_server.game.state import PlayerGameStates, GameMap
from play_tanks_server.game.state.actions import ACTION_TYPE as A, Action, VectorAction


class GameWorld(GameObject):

    def __init__(self, map: GameMap, max_players: int = 16):
        super().__init__()
        self.init_logger()  # Initialise logger after GameObject init
        self._encoded = None
        self._encoded_aabb = []
        self._lock = threading.Lock()
        self.max_players = max_players

        self.players = PlayerGameStates(max_players)
        self.map = map
        self.collision = CollisionGridHeap(cell_size=10)
        
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
        # For now do this here
        if isinstance(player, PlayerAI):
            player.computer.initialise(
                self.players.players[player].tank,
                self.map.network
            )

    @with_world_lock
    @with_exception_context
    @with_function_logger
    def leave(self, player: Player):
        """ Remove a player from the game world. """
        self.players.remove(player)

    @with_world_lock
    @with_exception_context
    @with_function_logger
    def initialise(self):
        """ Initialise the game world to start state. """
        self.game_time = 0.0
        self.game_tick = -1
        self.players.reset()
        self.collision.reset()
        self._encoded = None  # Invalidate cached encoded state
        spawn_points = self.map.get_spawn_points(len(self.players))
        for state in self.players.players.values():
            state.tank.set_position(spawn_points.pop())
            self.collision.add_entity(state.tank)

    @with_world_lock
    @with_exception_context
    @with_function_logger
    def reset(self):
        """ Reset the game world to initial state. """
        self.game_time = 0.0
        self.game_tick = -1
        self.players.reset()
        self._encoded = None  # Invalidate cached encoded state

    @with_world_lock
    @with_function_logger(disabled=True)
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
        self._encoded = None  # Invalidate cached encoded state
        self._handle_tank_movement(delta_time)
        self._handle_entity_movement(delta_time)
        self._handle_tank_barrel_rotation(delta_time)
        self._handle_tank_shooting(delta_time)
        self._handle_entity_updates(delta_time)
        self._handle_ai_players(delta_time)
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
        # First add all aabb with movement to the heap
        timer = self.logger.time('heap_init_dynamic')
        self.collision.update_events(delta_time)
        timer.stop()
        # Resolve movements
        process_timer = self.logger.time('process_events')
        for event in self.collision.heap():
            source = event.entity
            if source.is_destroyed:
                continue
            timer = self.logger.time('process_event_stage1')

            # Move entity to collision point
            if event.velocity is not None:
                source.set_velocity(event.velocity)
                self.collision.uncollide(event)

            # Apply damage
            source_hit = False
            for intersection in event.intersections:
                intersection.target.apply_damage(source)
                source.apply_damage(intersection.target)  # Take damage from target.
                source_hit = True
            timer.stop()

            # Check if entity is alive or has time remaining
            if source.is_destroyed or (1 - event.time) <= 0:
                continue

            timer = self.logger.time('process_event_stage2')
            # Recompute movement collision
            if source_hit and isinstance(source, Projectile):
                # Projectile should bounce on collision
                velocity = pe.calculate_bounce_velocity(source, event.intersections)
                source.set_velocity(velocity)
            elif source_hit and isinstance(source, Tank):
                # Tank should move in direction that is not stuck.
                velocity = pe.calculate_tank_slide(source, event.intersections)
                source.set_velocity(velocity)
            timer.stop()
            
            timer = self.logger.time('process_event_stage3')
            # Update the aabb
            self.collision.update_event(event, delta_time)
            # Find earliest intersection.
            event.intersections.set_time(1.0)  # Set to max time
            # Only check for collisions if entity is moving
            if source.velocity.magnitude() > 0:
                for target_event in self.collision.events(event):
                    if event.intersections.includes(target_event.entity):
                        continue  # Ignore already processed intersections
                    intersection = pe.calculate_entity_intersection(source, target_event.entity,
                                                                    source_time=event.time,
                                                                    target_time=target_event.time,
                                                                    scalar=delta_time)
                    event.intersections.add(intersection)
            timer.stop()
            self.collision.insert_event(event, delta_time)
        process_timer.stop()

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
            projectile = state.tank.fire()
            if projectile is not None:
                self.collision.add_entity(projectile)

    @with_function_logger(context="game_update")
    def _handle_entity_updates(self, delta_time: float):
        """ Handle entity updates. """
        for state in self.players:  # Iterate over all players, including destroyed ones
            state.tank.update()
            state.tank.clear_velocity()  # stop movement until user input.
            if state.tank.is_destroyed:
                self.collision.remove_entity(state.tank)
            for projectile in state.tank.projectiles:
                if projectile.is_destroyed:
                    self.collision.remove_entity(projectile)

    @with_function_logger(context="game_ai")
    def _handle_ai_players(self, delta_time: float):
        """ Handle AI player actions. """
        for state in self.players.alive():
            player = state.player
            if not isinstance(player, PlayerAI) or True:
                continue
            player.computer.update([t for t in self.players.tanks() if t != state.tank])
            direction = player.computer.target_direction()
            state.set_action(VectorAction(direction, A.MOVE, player))
                

    def encode(self) -> EncodedGameWorld:
        """ Convert the game world state to serialisable game data. """
        if self._encoded is None:
            self._encoded = EncodedGameWorld(
                uid=self.uid,
                started=self.started,
                tick=self.game_tick,
                time=self.game_time,
                map_size=self.map.size,
                players=[state.player.encode() for state in self.players],
                entities=[
                    wall.encode() for wall in self.map.walls
                ] + [
                    entity.encode() for entity in self.players.entities()
                ],
                data={
                    'aabb': self._encoded_aabb
                }
            )
        return self._encoded