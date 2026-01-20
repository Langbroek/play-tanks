import heapq
from typing import Dict, Iterator, List, Union, overload

from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.engine.math.shapes import Rectangle
from play_tanks_server.game.engine.collisions import Intersection2D, Intersections2D, CollisionEvent
from play_tanks_server.game.objects.entity import Entity, DynamicEntity


class CollisionGridHeap:

    def __init__(self, cells_x: int, cells_y: int, delta_time: float = 1.0):
        """ Initialise the collision grid heap. """
        self.cells_x = cells_x
        self.cells_y = cells_y
        self.delta_time = delta_time
        self._grid: Dict[tuple, List[CollisionEvent]] = {}
        self._heap: List[CollisionEvent] = []
        self._blocked_intersections: Dict[CollisionEvent, List[Intersection2D]] = {}

    @overload
    def add_entity(self, entity: DynamicEntity, static: bool = False): ...
    @overload
    def add_entity(self, entity: Entity, static: bool = True): ...
    def add_entity(self, entity: Union[Entity, DynamicEntity], static: bool = False):
        """ 
        Add an entity to the collision grid heap. If entity is static, 
        it won't be used for movement calculations. 
        """
        aabb = entity.hit_box.aabb()
        if not static:
            aabb.expand(entity.get_displacement(1, scalar=self.delta_time))
        event = CollisionEvent(entity, aabb=aabb, static=static)
        self._add_event_to_grid(event)

    def has_events(self) -> bool:
        """ Check if there are any events in the heap. """
        return len(self._heap) > 0
    
    def pop_event(self) -> CollisionEvent[DynamicEntity]:
        """ Pop the event with the smallest time from the heap. """
        return heapq.heappop(self._heap)

    def insert_event(self, event: CollisionEvent[DynamicEntity]):
        """ Insert an event back into the heap. """
        heapq.heappush(self._heap, event)

    def recompute_events(self, source_event: CollisionEvent[DynamicEntity], event_type: str = 'hit'):
        """ 
        All events that depend on this entity need to be recomputed if event has hit. 
        Also clears all blocked collisions for this entity. 
        """
        modified = False
        for event in self._heap:
            if event is source_event:
                continue
            # Only compute if event hit and target is events's entity
            # Or if the source event blocks this event's entity
            if ((event_type == 'hit' and event.intersections.includes(source_event.entity) or
                 event_type == 'block' and self._clear_blocked_intersections(event, source_event))):
                event.intersections.clear()
                event.transform = None
                modified = True
        if modified:
            heapq.heapify(self._heap)

    def blocked_intersections(self, event: CollisionEvent) -> List[Intersection2D]:
        """ Returns the list of blocked normals for the given event's entity. """
        return self._blocked_intersections.get(event, [])
    
    def update_event_time(self, event: CollisionEvent):
        """ Sets the event time to the collision time if available. """
        event.time = event.intersections.time

    def non_blocked_grid_events(self, event: CollisionEvent) -> Iterator[CollisionEvent]:
        """ Returns all events in the same grid cells as the given event for alive entities only. """
        gx1, gy1, gx2, gy2 = self._aabb_to_grid_cells(event.aabb)
        seen = set()
        blocked = [intersection.target for intersection in self._blocked_intersections.get(event, [])]
        for cell_x in range(gx1, gx2 + 1):
            for cell_y in range(gy1, gy2 + 1):
                cell_key = (cell_x, cell_y)
                for cell_event in self._grid.get(cell_key, []):
                    if (cell_event.entity.is_destroyed or cell_event.entity in seen or 
                        cell_event.entity == event.entity or cell_event.entity in blocked):
                        continue
                    seen.add(cell_event.entity)
                    yield cell_event

    def update_event_aabb(self, event: CollisionEvent[DynamicEntity], distance_cap: float = 1.0):
        """ Updates the event's AABB based on the entity's displacement capped by distance_cap. """
        displacement = event.entity.get_displacement(distance_cap - event.time, 
                                                     scalar=self.delta_time)
        old_gx1, old_gy1, old_gx2, old_gy2 = self._aabb_to_grid_cells(event.aabb)
        event.aabb = event.entity.hit_box.aabb()
        event.aabb.expand(displacement)
        new_gx1, new_gy1, new_gx2, new_gy2 = self._aabb_to_grid_cells(event.aabb)
        if (old_gx1, old_gy1, old_gx2, old_gy2) == (new_gx1, new_gy1, new_gx2, new_gy2):
            return  # No change in grid cells
        
        for cell_x in range(min(old_gx1, new_gx1), max(old_gx2, new_gx2) + 1):
            for cell_y in range(min(old_gy1, new_gy1), max(old_gy2, new_gy2) + 1):
                if (cell_x < new_gx1 or cell_x > new_gx2 or
                    cell_y < new_gy1 or cell_y > new_gy2):
                    # Cell is no longer occupied, remove event
                    cell_key = (cell_x, cell_y)
                    events = self._grid.get(cell_key, [])
                    if event in events:
                        events.remove(event)

    def update_event_intersections(self, event: CollisionEvent[DynamicEntity], 
                                  intersections: Intersections2D):
        """ Updates the event's intersection data and compute the transform at collision time. """
        event.intersections = intersections

        displacement = event.entity.get_displacement(event.time_at_intersection, 
                                                     scalar=self.delta_time)
        event.transform = event.entity.transform.translated(displacement)
        # Add intersection to event blocked intersections if it has entity.
        self._add_event_blocked_intersections(event)

    def _add_event_to_grid(self, event: CollisionEvent):
        """ Internal method to add an event to the grid structure. """
        # Determine which grid cells the event occupies
        gx1, gy1, gx2, gy2 = self._aabb_to_grid_cells(event.aabb)
        for cell_x in range(gx1, gx2 + 1):
            for cell_y in range(gy1, gy2 + 1):
                cell_key = (cell_x, cell_y)
                if cell_key not in self._grid:
                    self._grid[cell_key] = []
                self._grid[cell_key].append(event)
        if not event.static:
            heapq.heappush(self._heap, event)

    def _aabb_to_grid_cells(self, aabb: Rectangle) -> tuple:
        """ Converts an AABB to grid cell coordinates. Returns (min_x, min_y, max_x, max_y). """
        return (
            int(aabb.x1 // self.cells_x),
            int(aabb.y1 // self.cells_y),
            int(aabb.x2 // self.cells_x),
            int(aabb.y2 // self.cells_y),
        )

    def _clear_blocked_intersections(self, source: CollisionEvent, target: CollisionEvent) -> bool:
        """ 
        Based on target entity, remove all blocked events for the source that might have been 
        blocked by target.
        """
        if target.stale:
            return False
        blocked = self._blocked_intersections.get(source, [])
        if len(blocked) == 0:
            return False
        for intersection in blocked:
            if intersection.target != target.entity:
                continue
            blocked.remove(intersection)
            return True
        return False

    def _add_event_blocked_intersections(self, event: CollisionEvent):
        """ 
        Adds the event's intersection to the blocked intersections if it has a target entity. 
        """
        if event.intersections.empty():
            return
        blocked = self._blocked_intersections.setdefault(event, [])
        for intersection in event.intersections:
            if intersection not in blocked:
                blocked.append(intersection)
