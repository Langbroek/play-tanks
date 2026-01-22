import heapq
import itertools
import tqdm

from typing import Dict, List, Tuple, Iterator

from play_tanks_server.game.engine.algorithm import WaypointGrid, SegmentGrid
from play_tanks_server.game.engine.physics import engine as pe
from play_tanks_server.game.engine.math import Vec2, Transform, Waypoint
from play_tanks_server.game.engine.math.shapes import Segment


class WaypointConnection:
    def __init__(self, source: Waypoint, target: Waypoint, segment: Segment):
        self.source = source
        self.target = target
        self.segment = segment
        self.cost = segment.length

    def get_target(self, source_waypoint: Waypoint) -> Waypoint:
        if source_waypoint == self.source:
            return self.target
        elif source_waypoint == self.target:
            return self.source
        raise ValueError("Source waypoint not part of this path.")
    
    def __hash__(self):
        return hash((self.source, self.target))
    
    def __eq__(self, value):
        if not isinstance(value, WaypointConnection):
            return False
        return ((self.source == value.source and self.target == value.target) or
                (self.source == value.target and self.target == value.source))


def waypoint_path_in_waypoint_paths(path: List[Waypoint], waypoint_paths: List[List[Waypoint]]) -> bool:
    for wp_path in waypoint_paths:
        if len(wp_path) != len(path):
            continue
        if all(wp1 == wp2 for wp1, wp2 in zip(wp_path, path)):
            return True
    return False


def find_all_paths(waypoint_paths: Dict[Waypoint, List[WaypointConnection]]):
    """ Brute force all paths between waypoints. """
    import time
    start_time = time.time()
    routes = {}
    return
    def traverse(waypoint: Waypoint, paths: List[Waypoint], visited: set[Waypoint]):
        for path in waypoint_paths.get(waypoint, []):
            next_wp = path.get_target(waypoint)
            if next_wp in visited:
                continue
            new_paths = paths + [next_wp]
            routes.setdefault(paths[0], []).append(new_paths)
            traverse(next_wp, new_paths, visited | {next_wp})

    for waypoint, paths in waypoint_paths.items():
        traverse(waypoint, [waypoint], set([waypoint]))

    # Organise routes by waypoint to waypoint
    grouped_routes: Dict[Tuple[Waypoint, Waypoint], List[List[Waypoint]]] = {}
    for start_wp, all_paths in routes.items():
        for path in all_paths:
            end_wp = path[-1]
            group = (start_wp, end_wp)
            inverse_group = (end_wp, start_wp)
            if group not in grouped_routes and inverse_group in grouped_routes:
                group = inverse_group  # Flip.
                path = path[::-1]
            if not waypoint_path_in_waypoint_paths(path, grouped_routes.get(group, [])):
                grouped_routes.setdefault(group, []).append(path)
            
    end_time = time.time()
    print(f"Computed all waypoint paths in {end_time - start_time:.4f} seconds.")
    print(len(routes), "waypoints with paths found.")



class WaypointMap:

    def __init__(self, angle_threshold: float = 60.0):
        self.angle_threshold = angle_threshold
        self.connection: Dict[Waypoint, List[WaypointConnection]] = {}
        self._count = 0

    def add(self, source: Waypoint, target: Waypoint, segment: Segment):
        connection = WaypointConnection(source, target, segment)
        self.connection.setdefault(source, []).append(connection)
        self.connection.setdefault(target, []).append(connection)
        self._count += 1
    
    def __len__(self) -> int:
        """ Return the number of connections in the map. """
        return self._count

    def optimise(self):
        """ Remove all redundant connections, based on thresholded angle. """
        remove_connections: List[WaypointConnection] = []
        visited = set()
        with tqdm.tqdm(total=self._count, desc="Optimising Waypoint Map") as pbar:
            for waypoint, connections in self.connection.items():
                for con_a in connections:
                    pbar.update(1)
                    if con_a in visited:
                        continue  # already processed
                    waypoint_a = con_a.get_target(waypoint)
                    for con_b in connections:
                        if con_a == con_b:
                            continue
                        waypoint_b = con_b.get_target(waypoint)
                        # need close enough .
                        if not pe.points_are_nearly_collinear_2d(
                            waypoint.position,
                            waypoint_a.position,
                            waypoint_b.position,
                            threshold_degrees=self.angle_threshold
                        ):
                            continue
                        # Check if waypoint_a lies on segment waypoint - waypoint_b
                        if not pe.point_lies_on_segment_collinear_2d(
                            waypoint_a.position,
                            Segment(waypoint.position, waypoint_b.position)
                        ):
                            continue
                        # Remove con_a as it is redundant
                        remove_connections.append(con_b) 
                    visited.add(con_a)  
        print('Optimised Waypoint Map: Removed', len(remove_connections), 'redundant connections.')
        for con in remove_connections:
            self.remove(con)

    def remove(self, connection: WaypointConnection):
        """ Remove a connection from the map. """
        removed = False
        if connection in self.connection.get(connection.source, []):
            self.connection[connection.source].remove(connection)
            removed = True
        if connection in self.connection.get(connection.target, []):
            self.connection[connection.target].remove(connection)
            removed = True
        if removed:
            self._count -= 1

    def clear(self):
        """ Clear the waypoint map. """
        self.connection.clear()
        self._count = 0

    def values(self) -> Iterator[WaypointConnection]:
        """ Iterate over all connections in the map. """
        seen = set()
        for connections in self.connection.values():
            for connection in connections:
                if connection in seen:
                    continue
                seen.add(connection)
                yield connection


class WaypointNetwork:
    def __init__(self, offset: float, hulls: List[Segment], corners: List[Transform], 
                 cell_size: float = 20, threshold: float = 2.0, 
                 collinear_angle: float = 60.0):
        self._hulls = hulls
        self.hull_grid = SegmentGrid(cell_size, hulls)
        self.waypoint_grid = WaypointGrid(cell_size)
        self.waypoint_map = WaypointMap(collinear_angle)

        self._offset = offset
        self._hulls = hulls
        self._corners = corners
        self._threshold = threshold
        self._initialise()

    def _initialise(self):
        """ Initialise the waypoint network. """
        self.waypoint_grid.clear()
        duplicates = 0
        for transform in self._corners:
            wp = Waypoint(transform.advanced(self._offset).position, len(self.waypoint_grid))
            for grid_wp in self.waypoint_grid.values(value=wp):
                if grid_wp is wp:
                    continue
                if pe.vector_in_proximity(wp.position, grid_wp.position, threshold=self._threshold):
                    duplicates += 1
                    break  # Skip adding duplicate waypoint
            else:
                self.waypoint_grid.insert(wp)
        print(f'Skipped {duplicates} duplicate waypoints out of {len(self._corners)} corners.')

        # Setup waypoint map by finding all posible connections with line of sight.
        self.waypoint_map.clear()
        combinations = itertools.combinations(self.waypoint_grid.values(), 2)
        non_opt_count = 0
        opt_count = 0
        for start, end in tqdm.tqdm(combinations, desc="Building Waypoint Map",
                                    total=len(self.waypoint_grid)*(len(self.waypoint_grid)-1)//2):
            segment = Segment(start.position, end.position)
            hulls = list(self.hull_grid.values(segment=segment))
            opt_count += len(hulls)
            non_opt_count += len(self._hulls)
            if pe.segment_intersects_segments_2d(segment, hulls):
                continue
            # Include offset checks so paths don't hug corners too tightly.
            intersects = False
            for scale in [self._offset, -self._offset]:
                offset = segment.normal * (scale * .7)
                perp_segment = segment.translated(offset)
                perp_hulls = list(self.hull_grid.values(segment=perp_segment))
                if pe.segment_intersects_segments_2d(perp_segment, perp_hulls):
                    intersects = True
                    break
            if intersects:
                continue
            self.waypoint_map.add(start, end, segment)
        print(f'Waypoint Map: {len(self.waypoint_map)} connections added. '
                f'Checked {non_opt_count} hulls ({opt_count} optimised).')  
        self.waypoint_map.optimise()

    def get_line_of_sight_waypoints(self, position: Vec2) -> List[Waypoint]:
        """ 
        Return all waypoints that have line of sight to the given position from 
        smallest to largest distance. 
        """
        return []
        visible_waypoints = []
        for waypoint in self.waypoint_paths.keys():
            segment = Segment(position, waypoint.position)
            if pe.segment_intersects_segments_2d(segment, self._hulls):
                continue
            visible_waypoints.append((segment.length, waypoint))

        visible_waypoints.sort(key=lambda x: x[0])
        return [wp for _, wp in visible_waypoints]