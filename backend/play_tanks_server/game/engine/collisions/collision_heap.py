import heapq
from typing import Dict, Iterator, List, Union

from play_tanks_server.game.engine.algorithm import CellGrid
from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.engine.math.shapes import Rectangle
from play_tanks_server.game.engine.collisions import Intersection2D, Intersections2D, CollisionEvent
from play_tanks_server.game.objects.entity import Entity, DynamicEntity, StaticEntity


class CollisionGridHeap:

    def __init__(self, cell_size: int = 50):
        """ Initialise the collision grid heap. """
        self._static_grid = CellGrid[CollisionEvent](cell_size)
        self._grid = CellGrid[CollisionEvent](cell_size)
        self._heap: List[CollisionEvent[DynamicEntity]] = []
        # Map of entity blocking collisions.
        self._collided_events: Dict[Entity, List[CollisionEvent[DynamicEntity]]] = {}

    def reset(self, static: bool = False):
        """ Reset the collision grid heap. """
        self._heap.clear()
        self._grid.clear()
        self._collided_events.clear()
        if static:
            self._static_grid.clear()

    def add_static_entity(self, entity: StaticEntity):
        """ Add a static entity to the static collision grid that are initalised once. """
        aabb = entity.hit_box.aabb()
        event = CollisionEvent(entity, aabb=aabb, static=True)
        self._static_grid.insert(event)

    def add_entity(self, entity: Union[Entity, DynamicEntity]):
        """ 
        Add an entity to the live collision heap. 
        """
        aabb = entity.hit_box.aabb()
        event = CollisionEvent(entity, aabb=aabb, static=False)
        self._grid.insert(event)
        heapq.heappush(self._heap, event)

    def insert_event(self, event: CollisionEvent[DynamicEntity], delta_time: float):
        """ Insert an event back into the heap. """
        if len(event.intersections) > 0:
            for collision in event.intersections:
                self._collided_events.setdefault(collision.target, []).append(event)
            cap = event.intersections._time
        else:
            cap = 1.0
        velocity = event.entity.get_displacement(cap - event.time, scalar=delta_time)
        event.velocity = velocity

        heapq.heappush(self._heap, event)

    def update_event(self, event: CollisionEvent[DynamicEntity], delta_time: float):
        """ Update a single event in the grid heap. """
        aabb = event.entity.hit_box.aabb()
        aabb.expand(event.entity.get_displacement(1.0 - event.time, scalar=delta_time))
        event.aabb = aabb
        self._grid.update(event)

    def update_events(self, delta_time: float):
        """ Update all active entities in the grid heap and expand their aabb based on movement. """
        for event in list(self._grid.values()):
            self.update_event(event, delta_time)
    
    def heap(self) -> Iterator[CollisionEvent[DynamicEntity]]:
        """ Iterates the heap till no more events are left. """
        while len(self._heap) > 0:
            event = heapq.heappop(self._heap)
            yield event

    def uncollide(self, event: CollisionEvent[DynamicEntity]):
        """ Remove the event entity from any collided intersections. """
        if event.entity not in self._collided_events:
            return
        events = self._collided_events.pop(event.entity)
        for collision_event in events:
            collision_event.intersections.remove_by_target(event.entity)

    def events(self, entity: Entity) -> Iterator[CollisionEvent[DynamicEntity]]:
        """ Return all the events that involve the given entity. """
        yield from self._grid.values(value=entity)


