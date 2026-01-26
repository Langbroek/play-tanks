from typing import Generic, Tuple, Union, Iterator, Iterable, Optional, List, Protocol
from typing_extensions import TypeVar

from play_tanks_server.game.engine.math.shapes import Segment


T = TypeVar('T')


COORD_XY = Tuple[float, float]
COORD_XYXY = Tuple[float, float, float, float]

CELL = Tuple[int, int]


class CellItem(Protocol, Generic[T]):
    """ 
    Protocol for items that can be stored in a CellGrid.
    """
    def to_cell_coords(self) -> Union[COORD_XY, COORD_XYXY]:
        ...


class CellGrid(Generic[T]):

    def __init__(self, cell_size: float, items: Optional[Iterable[CellItem[T]]] = None):
        self.cell_size = cell_size
        self._grid: dict[CELL, List[T]] = {}
        self._item_coords: dict[T, Tuple[int, int, int, int]] = {}
        self._count = 0
        if items is not None:
            for item in items:
                self.insert(item)
    
    def _world_to_cell(self, value: float, eps: float = 1e-6) -> int:
        """ Convert a world coordinate to a cell index. """
        return int((value - eps) // self.cell_size)

    def _coords_to_cell(self, coords: Union[COORD_XY, COORD_XYXY]) -> Tuple[int, int, int, int]:
        """ Convert coordinates to cell indices. """
        if len(coords) == 2:
            x, y = coords
            cell_x = self._world_to_cell(x)
            cell_y = self._world_to_cell(y)
            return (cell_x, cell_y, cell_x, cell_y)
        elif len(coords) == 4:
            x1, y1, x2, y2 = coords
            x1, y1, x2, y2 = min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
            return (self._world_to_cell(x1), self._world_to_cell(y1),
                    self._world_to_cell(x2), self._world_to_cell(y2))
        
    def insert(self, item: CellItem[T]):
        """ Insert an item into the grid. """
        coords = item.to_cell_coords()
        for cell in self._iter_cells(coords):
            self._insert_single_cell(item, cell)
        self._item_coords[item] = self._coords_to_cell(coords)  # Cache the coords
    
    def _iter_cells(self, coords: Union[COORD_XY, COORD_XYXY]) -> Iterator[CELL]:
        gx1, gy1, gx2, gy2 = self._coords_to_cell(coords)
        if gx1 == gx2 and gy1 == gy2:
            yield (gx1, gy1)
            return
        for cell_x in range(gx1, gx2 + 1):
            for cell_y in range(gy1, gy2 + 1):
                yield (cell_x, cell_y)
    
    def _insert_single_cell(self, item: CellItem[T], cell: CELL):
        """ Inserts an item into a single cell. """
        cell_key = cell
        grid = self._grid.setdefault(cell_key, [])
        if item not in grid:
            grid.append(item)
            self._count += 1
    
    def _remove_single_cell(self, item: CellItem[T], cell: CELL):
        """ Removes an item from a single cell. """
        cell_key = cell
        grid = self._grid.get(cell_key, [])
        if item in grid:
            grid.remove(item)
            self._count -= 1

    def clear(self):
        """ Clear the grid. """
        self._grid.clear()
        self._count = 0
        self._item_coords.clear()

    def update(self, item: CellItem[T]):
        """ Update an item in the grid. """
        if item not in self._item_coords:
            raise KeyError(f"Item {item} not found in grid.")
        ox1, oy1, ox2, oy2 = self._item_coords[item]
        nx1, ny1, nx2, ny2 = self._coords_to_cell(item.to_cell_coords())
        if ox1 == nx1 and oy1 == ny1 and ox2 == nx2 and oy2 == ny2:
            return  # No change in cells
        
        x_overlap = nx1 <= ox2 and nx2 >= ox1
        y_overlap = ny1 <= oy2 and ny2 >= oy1
        if x_overlap and y_overlap:
            # Full overlap.
            coords = min(ox1, nx1), min(oy1, ny1), max(ox2, nx2), max(oy2, ny2)
            for cell in list(self._iter_cells(coords)):
                x, y = cell
                if x < nx1 or x > nx2 or y < ny1 or y > ny2:
                    # Remove from old cells not in new
                    self._remove_single_cell(item, cell)
                elif x < ox1 or x > ox2 or y < oy1 or y > oy2:
                    # Add to new cells not in old
                    self._insert_single_cell(item, cell)
                # Ignore cells that are in both old and new
        else:
            # for simplicity, treat as no overlap
            for cell in list(self._iter_cells((ox1, oy1, ox2, oy2))):
                self._remove_single_cell(item, cell)
            for cell in list(self._iter_cells((nx1, ny1, nx2, ny2))):
                self._insert_single_cell(item, cell)

    
    def values(self, key: Optional[CELL] = None, keys: Optional[Iterable[CELL]] = None, 
               value: Optional[CellItem[T]] = None, values: Optional[Iterable[CellItem[T]]] = None, 
               segment: Optional[Segment] = None) -> Iterator[T]:
        """ 
        Iterate over all values in the grid associated to any of the provided parameters. 
        if no parameters are set, all values in the grid are returned.
        """
        seen = set()
        if segment is not None:
            for cell in self._iter_segment_cells(segment):
                yield from self._iter_unique_items_in_cell(cell, seen)
            return
        
        keys = [key] if key is not None else keys
        if keys:
            for k in keys:
                yield from self._iter_unique_items_in_cell(k, seen)
            return
        
        values = [value] if value is not None else values
        if values:
            for val in values:
                coords = val.to_cell_coords()
                for cell in self._iter_cells(coords):
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
        # start / end in world space
        w_x1, w_y1 = segment.start.x, segment.start.y
        w_x2, w_y2 = segment.end.x, segment.end.y
        # start / end in grid space
        g_x1, g_y1 = self._world_to_cell(w_x1), self._world_to_cell(w_y1)
        g_x2, g_y2 = self._world_to_cell(w_x2), self._world_to_cell(w_y2)
        # World deltas
        w_dx = w_x2 - w_x1
        w_dy = w_y2 - w_y1

        # Vertical line case
        if abs(w_dx) < 1e-9:
            step_y = 1 if w_dy > 0 else -1
            for y in range(g_y1, g_y2 + step_y, step_y):
                yield (g_x1, y)
            return
        # Horizontal line case
        if abs(w_dy) < 1e-9:
            step_x = 1 if w_dx > 0 else -1
            for x in range(g_x1, g_x2 + step_x, step_x):
                yield (x, g_y1)
            return
        # General case using 2D DDA algorithm
        step_x = 1 if w_dx > 0 else -1
        step_y = 1 if w_dy > 0 else -1

        t_delta_x = self.cell_size / abs(w_dx)
        t_delta_y = self.cell_size / abs(w_dy)

        next_x = (g_x1 + (1 if step_x > 0 else 0)) * self.cell_size
        next_y = (g_y1 + (1 if step_y > 0 else 0)) * self.cell_size

        t_max_x = (next_x - w_x1) / w_dx
        t_max_y = (next_y - w_y1) / w_dy

        x, y = g_x1, g_y1
        yield (x, y)
        while (x, y) != (g_x2, g_y2):
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

