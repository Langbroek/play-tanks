from typing import Tuple, Optional, Iterable

from play_tanks_server.game.engine.math import Transform, Vec2
from play_tanks_server.game.engine.math.shapes import Segment
from play_tanks_server.game.events import CollisionEvent
from play_tanks_server.game.objects import Tank, StaticEntity, DynamicEntity, Projectile
from play_tanks_server.game.objects.collisions import HitBox
from play_tanks_server.game.state import GameMap


debug_params = {}


def calculate_tank_transform(tank: Tank, direction: Vec2, scalar: float) -> Transform:
    """ Calculate the new transform for a tank given a direction and scalar movement. """
    transform = tank.transform
    

def resolve_static_tank_collision(tank: Tank, entity: StaticEntity) -> Tuple[Transform, bool]:
    """ 
    Resolve collisions between a tank and the game map. 
    Returns a transform with new direction and position to avoid collision.
    """
    # TODO fix the self.collides call to use get_collisions
    collisions = entity.get_collisions(tank)
    if len(collisions) == 0:
        return tank.transform, False
    
    tank_hit_box = tank.hit_box()
    for collision in entity.hit_box():
        if tank_hit_box.collides(collision):
            # Simple collision resolution: move tank back along its velocity vector
            correction_vector = tank.get_velocity().normalized() * -0.1


def segment_intersection_2d(seg_a: Segment, seg_b: Segment, 
                            eps: float = 1e-9) -> Optional[Tuple[Vec2, float, float]]:
    """ 
    Calculate the intersection point of two 2D segments if they intersect.
    Returns the intersection point as Vec3F or None if no intersection.
    Based on

    P(t) = A + t (B - A)
    Q(u) = C + u (D - C)
    
    Solve
    A + t r = C + u s
    Where
    r = B - A
    s = D - C

    return None if no intersection within the segments.
    or point and seg_a scalar t and seg_b scalar u if they intersect.
    """
    r = seg_a.end - seg_a.start
    s = seg_b.end - seg_b.start

    r_s_cross_prod = r.x * s.y - r.y * s.x
    if abs(r_s_cross_prod) < eps:
        return None
    
    qp_vec = seg_b.start - seg_a.start
    qp_r_cross_prod = qp_vec.x * r.y - qp_vec.y * r.x

    t = (qp_vec.x * s.y - qp_vec.y * s.x) / r_s_cross_prod
    u = qp_r_cross_prod / r_s_cross_prod

    if 0 <= t <= 1 and 0 <= u <= 1:
        return Vec2(data=seg_a.start + t * r)
    
    return None


def segment_collision_distance(seg_a: Segment, col_a: Optional[HitBox], dst_a: float,
                               seg_b: Segment, col_b: Optional[HitBox], dst_b: float) -> float:
    """ 
    Calculate collision (intersection) where two segments intersect within max_distance.
    Id hitboxes are provided, use them for more accurate collision detection.
    If provided, check at both ends of the intersection and average distance.
    Both segments distance is normalised and scaled by the given scale factor.
    If no collision, return -1.
    dst_a is total traveled distance of seg_a from 0, 1
    dst_b is total traveled distance of seg_b from 0, 1
    """
    seg_b_length_norm = 0.0
    seg_a_length_norm = 0.0
    segments = [seg_a]
    global debug_params

    if col_b is not None:
        # Instead of using path segment, we will use path from hull forwards.
        # Find hull path thats closest to seg_a start
        # Normalise seg_b to length of hit_box_b
        seg_b_total_length = seg_b.length() if dst_b <= 0 else seg_b.length() / (1 - dst_b)
        seg_b_length_norm = col_b.length() / seg_b_total_length
        col_b.local_transform(seg_b.transform_from_start())


        if box_front_left.distance_to(seg_a.start) < box_front_right.distance_to(seg_a.start):
            seg_b = Segment(box_front_left, box_front_left.translated(seg_b.end))
        else:
            seg_b = Segment(box_front_right, box_front_right.translated(seg_b.end))

        debug_params['seg_b'] = seg_b
        debug_params['seg_b_length_norm'] = seg_b_length_norm

    if col_a is not None:
        seg_a_total_length = seg_a.length() if dst_a <= 0 else seg_a.length() / (1 - dst_a)
        seg_a_length_norm = col_a.length() / seg_a_total_length

        box_front_left, box_front_right = col_a.front_left_right()
        box_front_left.rotate_by_direction(seg_a.direction)
        box_front_right.rotate_by_direction(seg_a.direction)
        box_front_left.translate(seg_a.start)
        box_front_right.translate(seg_a.start)
        segments = [
            Segment(box_front_left, box_front_left.translated(seg_a.end)),
            Segment(box_front_right, box_front_right.translated(seg_a.end))
        ]
        debug_params['seg_a'] = segments
        debug_params['seg_a_length_norm'] = seg_a_length_norm

    collision_distances = []
    for segment in segments:
        intersection = segment_intersection_2d(segment, seg_b)
        if intersection is None:
            continue
        _, seg_a_dist, seg_b_dist = intersection
        # Adjust distances based on hitbox lengths and dst_a, dst_b
        # since seg_a_dist is from 0 to 1 for the normalised segment of the left over distance.
        seg_a_dist = dst_a + (seg_a_dist * (1 - dst_a))
        seg_b_dist = dst_b + (seg_b_dist * (1 - dst_b))

        debug_params.setdefault('intersections', []).append((seg_a_dist, seg_b_dist))

        a_start, a_end = seg_a_dist - (seg_a_length_norm / 2), seg_a_dist + (seg_a_length_norm / 2)
        b_start, b_end = seg_b_dist - (seg_b_length_norm / 2), seg_b_dist + (seg_b_length_norm / 2)
        overlap_start = max(a_start, b_start)
        overlap_end = min(a_end, b_end)
        if overlap_start <= overlap_end:
            collision_distances.append(overlap_start)
    if len(collision_distances) == 0:
        return -1.0
    return min(collision_distances) - dst_a  # Return distance from seg_a start
            

def resolve_projectile_collision(projectile: Projectile, entities: Iterable[DynamicEntity], 
                                 game_map: GameMap, delta_time: float
                                 ) -> CollisionEvent[Projectile]:
    """
    Calculate the nearest collision event for a projectile with entities and the game map.
    Returns a CollisionEvent if a collision is detected, otherwise None.
    """
    p_segment = projectile.segment(delta_time)
    p_hit_box = projectile.hit_box()
    p_traveled = projectile.distance_traveled(delta_time)

    event = CollisionEvent(projectile, None, p_traveled)

    for entity in entities:
        # Ignore self
        if entity is projectile:
            continue
        t_hit_box = entity.hit_box()
        t_segment = entity.segment(delta_time)
        t_traveled = entity.distance_traveled(delta_time)
        c_dist = segment_collision_distance(p_segment, p_hit_box, p_traveled,
                                            t_segment, t_hit_box, t_traveled)
        if c_dist >= 0 and c_dist < event.distance:
            event = CollisionEvent(projectile, entity, c_dist)

    # for wall in game_map.walls:
    #     c_dist = segment_collision_distance(p_segment, p_hit_box, wall, None, distance)
    #     if c_dist >= 0 and c_dist < event.distance:
    #         event = CollisionEvent(projectile, None, c_dist)


def test2():

    import numpy as np
    import random
    from PIL import Image, ImageDraw
    global debug_params
    
    size = (1080, 1080)
    image = Image.fromarray(np.full((*size, 3), 255, dtype=np.uint8))
    draw = ImageDraw.Draw(image)

    segment_a = Segment(Vec2F(100, 100), Vec2F(900, 900))
    hit_box_a = HitBox(80, 40, True)
    hit_box_a.update(segment_a.transform_from_start())
    dst_a = 0.0
    colour_a = (0, 255, 0)

    segment_b = Segment(Vec2F(100, 900), Vec2F(900, 100))
    hit_box_b = HitBox(40, 40, True)
    hit_box_b.update(segment_b.transform_from_start())
    dst_b = 0.0
    colour_b = (0, 0, 255)

    draw.line([(segment_a.start.x, segment_a.start.y), (segment_a.end.x, segment_a.end.y)],
                fill=colour_a, width=2)
    draw.line([(segment_b.start.x, segment_b.start.y), (segment_b.end.x, segment_b.end.y)],
                fill=colour_b, width=2)
    
    # intersection_distance = segment_collision_distance(
    #     segment_a, hit_box_a, dst_a,
    #     segment_b, hit_box_b, dst_b
    # )

    if 'seg_a' in debug_params:
        for seg in debug_params['seg_a']:
            draw.line([(seg.start.x, seg.start.y), (seg.end.x, seg.end.y)],
                      fill=(0, 100, 0), width=1)
    if 'seg_b' in debug_params:
        seg = debug_params['seg_b']
        draw.line([(seg.start.x, seg.start.y), (seg.end.x, seg.end.y)],
                  fill=(0, 0, 100), width=1)
        
    # Draw hit boxes
    for box in [hit_box_a, hit_box_b]:
        if box.world is not None:
            draw.polygon([
                (box.world.top_left.x, box.world.top_left.y),
                (box.world.top_right.x, box.world.top_right.y),
                (box.world.bottom_right.x, box.world.bottom_right.y),
                (box.world.bottom_left.x, box.world.bottom_left.y)
            ], outline=(100, 100, 255))

    image.show()






if __name__ == "__main__":
    # Move this to test later

    test2()


