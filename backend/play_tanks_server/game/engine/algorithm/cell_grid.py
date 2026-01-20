from typing import Generic, Tuple, Union, Iterator, Iterable, Optional, List
from typing_extensions import TypeVar


from play_tanks_server.game.engine.math import Waypoint
from play_tanks_server.game.engine.math.shapes import Segment


T = TypeVar('T')


COORD_XY = Tuple[float, float]
COORD_XYXY = Tuple[float, float, float, float]

CELL = Tuple[int, int]


class CellGrid(Generic[T]):

    def __init__(self, cell_size: float, items: Optional[Iterable[T]] = None):
        self.cell_size = cell_size
        self._grid: dict[CELL, List[T]] = {}
        self._count = 0
        if items is not None:
            for item in items:
                self.insert(item)

    def _item_to_coords(self, item: T) -> Union[COORD_XY, COORD_XYXY]:
        """ Convert an item to coordinates. Must be implemented by subclasses. """
        raise NotImplementedError()

    def _coords_to_cell(self, coords: Union[COORD_XY, COORD_XYXY]) -> Tuple[int, int, int, int]:
        """ Convert coordinates to cell indices. """
        if len(coords) == 2:
            x, y = coords
            cell_x = int(x // self.cell_size)
            cell_y = int(y // self.cell_size)
            return (cell_x, cell_y, cell_x, cell_y)
        elif len(coords) == 4:
            x1, y1, x2, y2 = coords
            return (int(x1 // self.cell_size), int(y1 // self.cell_size),
                    int(x2 // self.cell_size), int(y2 // self.cell_size))
        
    def insert(self, item: T):
        """ Insert an item into the grid. """
        coords = self._item_to_coords(item)
        for cell in self._iter_cells(coords):
            self._insert_single_cell(item, cell)
    
    def _iter_cells(self, coords: Union[COORD_XY, COORD_XYXY]) -> Iterator[CELL]:
        gx1, gy1, gx2, gy2 = self._coords_to_cell(coords)
        if gx1 == gx2 and gy1 == gy2:
            yield (gx1, gy1)
            return
        for cell_x in range(gx1, gx2 + 1):
            for cell_y in range(gy1, gy2 + 1):
                yield (cell_x, cell_y)
    
    def _insert_single_cell(self, item: T, cell: Tuple[int, int]):
        """ Inserts an item into a single cell. """
        cell_key = cell
        grid = self._grid.setdefault(cell_key, [])
        if item not in grid:
            grid.append(item)
            self._count += 1

    def clear(self):
        """ Clear the grid. """
        self._grid.clear()
        self._count = 0
    
    def values(self, key: Optional[CELL] = None, keys: Optional[Iterable[CELL]] = None, 
               value: Optional[T] = None, values: Optional[Iterable[T]] = None, 
               segment: Optional[Segment] = None) -> Iterator[T]:
        """ 
        Iterate over all values in the grid associated to any of the provided parameters. 
        if no parameters are set, all values in the grid are returned.
        """
        seen = set()
        keys = [key] if key is not None else keys
        if keys:
            for k in keys:
                yield from self._iter_unique_items_in_cell(k, seen)
            return
        
        values = [value] if value is not None else values
        if values:
            for val in values:
                coords = self._item_to_coords(val)
                for cell in self._iter_cells(coords):
                    yield from self._iter_unique_items_in_cell(cell, seen)
            return
        
        if segment is not None:
            for cell in self._iter_segment_cells(segment):
                yield from self._iter_unique_items_in_cell(cell, seen)
            return
        
        # Fallback iterate all unique
        for cell in self._grid.keys():
            yield from self._iter_unique_items_in_cell(cell, seen)

    def _iter_unique_items_in_cell(self, cell: CELL, seen: Optional[set] = None) -> Iterator[T]:
        """ Iterate over unique items in a cell. """
        if seen is None:
            seen = set()
        for item in self._grid.get(cell, []):
            if item in seen:
                continue
            seen.add(item)
            yield item

    def _iter_segment_cells(self, segment: Segment) -> Iterator[CELL]:
        """ Ray cast through the grid cells that the segment passes through. """
        x1, y1 = int(segment.start.x // self.cell_size), int(segment.start.y // self.cell_size)
        x2, y2 = int(segment.end.x // self.cell_size), int(segment.end.y // self.cell_size)
        # Direction
        dx = x2 - x1
        dy = y2 - y1

        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1

        t_delta_x = self.cell_size / abs(dx) if dx != 0 else float('inf')
        t_delta_y = self.cell_size / abs(dy) if dy != 0 else float('inf')

        next_x = (x1 + (1 if step_x > 0 else 0)) * self.cell_size
        next_y = (y1 + (1 if step_y > 0 else 0)) * self.cell_size

        t_max_x = (next_x - segment.start.x) / dx if dx != 0 else float('inf')
        t_max_y = (next_y - segment.start.y) / dy if dy != 0 else float('inf')

        x, y = x1, y1
        yield (x, y)
        while (x, y) != (x2, y2):
            if t_max_x < t_max_y:
                t_max_x += t_delta_x
                x += step_x
            else:
                t_max_y += t_delta_y
                y += step_y
            yield (x, y)

    def __len__(self) -> int:
        """ Return the number of items in the grid. """
        return self._count

# Math grids.


class WaypointGrid(CellGrid[Waypoint]):
    def _item_to_coords(self, item: Waypoint) -> Tuple[float, float]:
        return (item.position.x, item.position.y)


class SegmentGrid(CellGrid[Segment]):
    def _item_to_coords(self, item: Segment) -> Tuple[float, float, float, float]:
        return (item.start.x, item.start.y, item.end.x, item.end.y)