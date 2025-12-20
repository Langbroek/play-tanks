import heapq

from play_tanks_server.game.events import CollisionEvent


class CollisionHeap:

    """ A min-heap to manage collision events based on their distance. """

    def __init__(self):
        self._heap = []

    def add(self, collision_event: CollisionEvent):
        """ Add a collision event to the heap. """
        heapq.heappush(self._heap, collision_event)

    def pop(self) -> CollisionEvent:
        """ Remove and return the collision event with the smallest distance. """
        return heapq.heappop(self._heap)
    
    def is_empty(self) -> bool:
        """ Check if the heap is empty. """
        return not self._heap