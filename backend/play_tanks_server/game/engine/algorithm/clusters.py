import numpy as np

from scipy.ndimage import label
from typing import Dict, List

from play_tanks_server.game.engine.math.shapes import Rectangle


def find_largest_rectangle(array: np.ndarray, feature_id: int) -> tuple:
    """ Find the largest rectangle for a given feature in a labeled array. """
    largest_shape = (None, 0)
    for (y, x), feature in np.ndenumerate(array):
        y, x = y + 1, x + 1  # adjust for slicing
        if feature != feature_id:
            continue
        area = np.sum(array[:y, :x] == feature_id)
        if area != y * x or area <= largest_shape[1]:
            continue
        largest_shape = ((y, x), area)
    if largest_shape[0] is None:
        return 0, 0
    return largest_shape[0]


def array_to_rectangles(array: np.ndarray) -> Dict[int, List[Rectangle[int]]]:
    """ Convert a 2D numpy array to a list of rectangles representing the filled areas. """
    if array.dtype != bool:
        array = array > 0
    labeled_array, _ = label(array)
    rectangles: Dict[int, List[np.ndarray]] = {i: [] for i in range(1, np.max(labeled_array) + 1)}
    for (y, x) in np.argwhere(labeled_array):
        feature_id = labeled_array[y, x]
        if feature_id == 0:
            continue
        end_y, end_x = find_largest_rectangle(labeled_array[y:, x:], feature_id)
        if end_y == 0 or end_x == 0:
            continue
        rectangles[feature_id].append(Rectangle(x, y, x + end_x, y + end_y))
        labeled_array[y:y + end_y, x:x + end_x] = 0  # Mark as processed
    return rectangles
