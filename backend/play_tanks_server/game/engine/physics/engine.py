import math
from typing import List, Tuple, Optional, Iterable

from play_tanks_server.game.engine.collisions import Intersection2D
from play_tanks_server.game.engine.math import Transform, Vec2
from play_tanks_server.game.engine.math.shapes import Segment, Rectangle
from play_tanks_server.game.objects import Tank, Entity, DynamicEntity, Wall


BASE_EPS = 1e-9


def calculate_bounce_velocity(entity: DynamicEntity, intersections: List[Intersection2D]) -> Vec2:
    """ Rotates the given entity's transform to reflect off the collision surface. """
    direction = entity.direction.normalised()
    for hull in [hull for inter in intersections for hull in inter.hulls]:
        if direction.dot(hull.normal) >= 0:
            continue  # Not colliding with this hull
        normal = hull.normal
        direction = direction - normal * 2 * direction.dot(normal)
    return direction


def segment_is_collinear(seg_a: Segment, seg_b: Segment, eps: float = BASE_EPS) -> bool:
    """ Check if two segments are colinear (lie on the same line). """
    if abs(seg_a.displacement.cross(seg_b.displacement)) >= eps:
        return False  # Not parallel
    a_to_b = seg_b.start - seg_a.start
    return abs(a_to_b.cross(seg_a.displacement)) < eps


def filter_intersection_normals(intersections: Iterable[Intersection2D]) -> List[Vec2]:
    """ 
    Filter normals from intersections, removing illegal ones and duplicates and 
    cancel out opposing normals that are illegal. 
    """
    legal: List[Vec2] = [] 
    illegal: List[Tuple[Segment, Vec2]] = []
    has_illegal = any(inter.illegal for inter in intersections)
    for (inter, hull) in ((inter, hull) for inter in intersections for hull in inter.hulls):
        normal = hull.opposite_normal if inter.invert_normal else hull.normal
        if not inter.illegal:
            if normal in legal:
                continue
            if has_illegal and inter.invert_normal:
                # Inverted normals are when hull is source and target corner, ignore these
                continue
            legal.append(normal)
            continue
        # Add to illegal normals
        can_add = True
        for i, existing in enumerate(illegal):
            tmp_hull, tmp_normal = existing
            normal_dot_tmp_normal = normal.dot(tmp_normal)
            if normal_dot_tmp_normal > 1 - BASE_EPS:
                # Same direction, no need to add.
                can_add = False
                break
            if not (normal_dot_tmp_normal < -1 + BASE_EPS):
                continue  # Not opposite, keep checking
            # Check if hull segments are same line, if so cancel opposites.
            if segment_is_collinear(hull, tmp_hull):
                # Remove opposite illegal normals
                illegal.pop(i)
                can_add = False
                break
        if can_add:
            illegal.append((hull, normal))
    for _, normal in illegal:
        if normal not in legal:
            legal.append(normal)
    return legal


def calculate_tank_slide(tank: Tank, intersections: List[Intersection2D]) -> Tuple[Vec2, float]:
    """ Calculates the sliding direction and velocity for a tank given a collision intersection. """
    velocity = tank.velocity
    for normal in filter_intersection_normals(intersections):
        velocity_dot_normal = velocity.dot(normal)
        if velocity_dot_normal >= 0:
            continue
            # continue  # Not blocked in this direction
        # Blocked in this direction, remove component
        velocity -= (normal * velocity_dot_normal)
    return velocity


def to_string(source: Segment, target: Segment, velocity: Vec2) -> str:
    """ Debugging function to print segment and velocity info. """
    return (f"Source Segment: Start({source.start.x}, {source.start.y}) "
            f"End({source.end.x}, {source.end.y})\n"
            f"Target Segment: Start({target.start.x}, {target.start.y}) "
            f"End({target.end.x}, {target.end.y})\n"
            f"Velocity: ({velocity.x}, {velocity.y})")


def near_zero(x: float, scale: float = 1.0, base_eps: float = BASE_EPS) -> bool:
    """ Check if x is near zero considering scale. """
    return abs(x) <= (base_eps * scale)


def vector_in_proximity(source: Vec2, target: Vec2, threshold: float = 0.0, 
                        base_eps: float = BASE_EPS) -> bool:
    """ Returns if a vector is within proximity of another vector given a threshold."""
    displacement = target - source
    distance = displacement.magnitude()
    return distance <= (threshold + base_eps)


def near_range(x: float, low: float, high: float, scale: float = 1.0, base_eps: float = BASE_EPS, 
               inclusive: bool = False) -> bool:
    """ Check if x is within [low, high] considering scale. """
    x = float(x)  # Convert incase its a np float
    if inclusive:
        return (x - base_eps * scale >= low) and (x + base_eps * scale <= high)
    return (x + base_eps * scale >= low) and (x - base_eps * scale <= high)


def point_lies_inside_aabb(point: Vec2, aabb: Rectangle, strict: bool = False) -> bool:
    """ Check if a point lies inside an axis-aligned bounding box. """
    if strict:
        return (aabb.x1 < point.x < aabb.x2) and (aabb.y2 < point.y < aabb.y1)
    return (aabb.x1 <= point.x <= aabb.x2) and (aabb.y2 <= point.y <= aabb.y1)


def point_orientation(a: Vec2, b: Vec2, c: Vec2) -> float:
    """
    Returns:
     > 0 if c is to the left of AB
     < 0 if c is to the right of AB
     = 0 if collinear
    """
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def point_lies_on_segment_collinear_2d(point: Vec2, segment: Segment, base_eps: float = BASE_EPS) -> bool:
    """ Check if point c lies on segment AB using orientation and bounding box. """
    return (
        near_range(
            point.x,
            min(segment.start.x, segment.end.x),
            max(segment.start.x, segment.end.x), 
            base_eps=base_eps) and
        near_range(
            point.y,
            min(segment.start.y, segment.end.y),
            max(segment.start.y, segment.end.y),
            base_eps=base_eps)
    )


def points_are_collinear_2d(a: Vec2, b: Vec2, c: Vec2, base_eps: float = BASE_EPS) -> bool:
    """ Check if three points are collinear in 2D space. """
    return near_zero((b - a).cross(c - a), base_eps=base_eps)


def points_are_nearly_collinear_2d(a: Vec2, b: Vec2, c: Vec2, threshold_degrees: float, 
                                   base_eps: float = BASE_EPS) -> bool:
    """ Check if three points are nearly collinear in 2D space within a threshold angle. """
    v1 = (a - b).normalised()
    v2 = (c - b).normalised()
    cos_angle = v1.dot(v2)

    cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to valid range
    angle_degrees = math.degrees(math.acos(cos_angle))
    return abs(angle_degrees - 180.0) <= threshold_degrees



def point_lies_between_segment(segment: Segment, point: Vec2) -> bool:
    """ Check if point b lies between points a and c. """
    dist_point_start = (point - segment.start).magnitude() ** 2
    dist_point_end = (point - segment.end).magnitude() ** 2
    dist_segment = (segment.end - segment.start).magnitude() ** 2
    if dist_segment + dist_point_end < dist_point_start:
        return False
    if dist_segment + dist_point_start < dist_point_end:
        return False
    return True


def point_lies_on_segment_2d(segment: Segment, point: Vec2, base_eps: float = BASE_EPS) -> bool:
    """ Check if a point lies on a given segment. """
    ap = point - segment.start
    ab = segment.displacement
    cross = ap.cross(ab)
    if not near_zero(cross, base_eps):
        return False  # Not on line
    dot = ap.dot(ab)
    if dot + base_eps < 0:
        return False  # Before start
    if dot - base_eps > ab.magnitude() ** 2:
        return False  # After end
    return True


def segment_intersection_2d_path(source: Segment, target: Segment, 
                                 velocity: Vec2, eps: float = BASE_EPS) -> float:
    """ 
    """
    a, b = source.start, source.end
    c, d = target.start, target.end
    p = c - a
    r = b - a
    q = d - c

    vxq = velocity.cross(q)
    if near_zero(vxq, eps):
        return -1.0
    
    t = p.cross(q) / vxq
    if not (0 <= t <= 1):
        return -1.0
    
    rxq = r.cross(q)
    qxr = q.cross(r)
    scale = abs(vxq) + abs(rxq) + abs(qxr) + 1.0
    if near_zero(rxq, scale, eps) or near_zero(qxr, scale, eps):
        # Parralel case if any segments on line its good.
        if (
            point_lies_between_segment(target, source.start) or 
            point_lies_between_segment(target, source.end)
        ):
            return t
        return -1.0
    
    pvt = velocity * t - p
    s = pvt.cross(q) / rxq
    if not near_range(s, 0, 1, scale, eps):
        return -1.0
    
    u = pvt.cross(r) / qxr
    if not near_range(u, 0, 1, scale, eps):
        return -1.0
    
    return t


def segment_intersects_segment_2d(source: Segment, target: Segment, eps: float = BASE_EPS) -> bool:
    """ Returns true if the source segment intersects the target segment. """
    o1 = point_orientation(source.start, source.end, target.start)
    o2 = point_orientation(source.start, source.end, target.end)
    o3 = point_orientation(target.start, target.end, source.start)
    o4 = point_orientation(target.start, target.end, source.end)

    # General case
    if (o1 * o2 < -eps) and (o3 * o4 < -eps):
        return True
    
    # Special Cases Collinear
    if near_zero(o1, eps) and point_lies_on_segment_collinear_2d(target.start, source, eps):
        return True
    if near_zero(o2, eps) and point_lies_on_segment_collinear_2d(target.end, source, eps):
        return True
    if near_zero(o3, eps) and point_lies_on_segment_collinear_2d(source.start, target, eps):
        return True
    if near_zero(o4, eps) and point_lies_on_segment_collinear_2d(source.end, target, eps):
        return True
    return False
        

def segment_intersects_segments_2d(source: Segment, targets: Iterable[Segment], eps: float = BASE_EPS) -> bool:
    """ Returns true if the source segment intersects any of the target segments. """
    for target in targets:
        if segment_intersects_segment_2d(source, target, eps):
            return True
    return False


def point_intersects_segment_2d(point: Vec2, segment: Segment, velocity: Vec2, eps: float = BASE_EPS) -> float:
    """
    Return time of intersetion of a point moving with a velocity vector to a given segment.
    """
    a, b = segment.start, segment.end
    p = a - point
    r = velocity
    q = b - a

    # No corner collisions
    if point == a or point == b:
        return -1.0

    vxq = velocity.cross(q)
    if near_zero(vxq, eps):
        return -1.0
    
    t = p.cross(q) / vxq
    if not (0 <= t <= 1):
        return -1.0
    
    rxq = r.cross(q)
    qxr = q.cross(r)
    scale = abs(rxq) + abs(qxr) + 1.0
    if near_zero(qxr, scale, eps) or near_range(rxq, scale, eps):
        # Parralel case if point on line its good.
        if point_lies_between_segment(segment, point):
            return t
        return -1.0
    
    pvt = velocity * t - p
    u = pvt.cross(r) / qxr
    if not near_range(u, 0, 1, scale, eps):
        return -1.0
    s = pvt.cross(q) / rxq
    if not near_range(s, 0, 1, scale, eps):
        return -1.0
    
    return t


def illegal_intersection_2d(source: Rectangle, target: Rectangle) -> Optional[Intersection2D]:
    """ Returns the intersection event if a source segment intersects the target rectangle. """
    hulls = []
    front_illegal = False
    for t_hull in target.hulls():
        for s_hull in [source.front(), source.left(), source.right()]:
            if t_hull in hulls:
                continue  # Already found intersection for this hull
            if s_hull.start == t_hull.start or s_hull.start == t_hull.end or \
               s_hull.end == t_hull.start or s_hull.end == t_hull.end:
                continue  # No corner collisions
            source_cross_target = s_hull.displacement.cross(t_hull.displacement)
            if near_zero(source_cross_target):
                continue  # Parallel segments
            t = (t_hull.start - s_hull.start).cross(t_hull.displacement) / source_cross_target
            if not near_range(t, 0, 1, inclusive=True):
                continue
            u = (t_hull.start - s_hull.start).cross(s_hull.displacement) / source_cross_target
            if not near_range(u, 0, 1, inclusive=True):
                continue
            hulls.append(t_hull)
            if s_hull == source.front():
                front_illegal = True
    if len(hulls) > 0 and front_illegal:
        return Intersection2D(
            time=0.0,
            hulls=hulls,
            illegal=True
        )
    return None


def hitbox_intersection_2d(hitbox: Rectangle, target_hitbox: Rectangle, velocity: Vec2, eps: float = BASE_EPS) -> Optional[Intersection2D]:
    """ 
    """
    # First check if hull has illegal intersection
    intersection = illegal_intersection_2d(hitbox, target_hitbox)
    if intersection is not None:
        return intersection
    
    source_segment = hitbox.front()
    intersections: List[Intersection2D] = []
    inverted_velocity = velocity * -1
    for target_segment in target_hitbox.hulls():
        if velocity.dot(target_segment.normal) >= 0:
            continue  # Not moving towards this hull
        for point in [source_segment.start, source_segment.end]:

            intersections.append(
                Intersection2D(
                    point_intersects_segment_2d(point, target_segment, velocity, eps),
                    hulls=[target_segment], 
                )
            )
        for point in [target_segment.start, target_segment.end]:
            intersections.append(
                Intersection2D(
                    point_intersects_segment_2d(point, source_segment, 
                                                inverted_velocity, eps), 
                    hulls=[source_segment], 
                    invert_normal=True
                )
            )
    result = None
    for inter in intersections:
        if inter.valid and (result is None or inter.time < result.time):
            result = inter
    return result


def calculate_entity_intersection(
    source: DynamicEntity,
    target: Entity,
    source_time: float = 0.0,
    target_time: float = 0.0,
    scalar: float = 1.0
) -> Intersection2D:
    """ Calculate the intersection between a dynamic source entity and a target entity. """
    time = 1.0 - source_time
    velocity = source.get_displacement(time, scalar=scalar)
    if isinstance(target, DynamicEntity):
        # Need to combine both velocities to create a static target and also move target if target_time is < source_time
        if target_time > source_time:
            raise NotImplementedError("Target time should not be greater than source.")
        target_offset = target.get_displacement(source_time - target_time, scalar=scalar)
        target_displacement = target.get_displacement(time, scalar=scalar) - target.get_displacement(source_time - target_time, scalar=scalar)
        velocity = velocity - target_displacement
        target_hitbox = target.hit_box.translated(target_offset)
    else:
        target_hitbox = target.hit_box

    result = hitbox_intersection_2d(source.hit_box, target_hitbox, velocity)
    if result is None:
        return Intersection2D(time=1.0)
    # Since intersection is from 0, 1 over the scale of 1.0 - source_time
    result.time = source_time + (time * result.time)
    result.target = target
    return result


def calculate_map_concave_corners(walls: List[Wall], map_aab: Rectangle) -> List[Transform]:
    """ Calculate all concave corners of the map walls as waypoints. """
    waypoints = []
    for wall in walls:
        t_hulls = [t_hull for t_wall in walls if t_wall != wall for t_hull in t_wall.hit_box.hulls()]
        for hull in wall.hit_box.hulls():
            point = hull.end
            for t_hull in t_hulls:
                if point_lies_on_segment_2d(t_hull, point):
                    point = None
                    break  # Any intersection and the point is convex and not concave.
            if point is not None and point_lies_inside_aabb(point, map_aab, strict=True):
                corner_normal = hull.direction.rotated_angle(-45)
                waypoints.append(Transform(point, corner_normal))
    return waypoints

            

