import cv2
import numpy as np
from scipy.ndimage import label
from typing import Dict, List

from play_tanks_server.game.engine.math import Vec2I, Line
from play_tanks_server.game.engine.math.shapes import Rectangle



def array_contours1(array: np.ndarray) -> List[List[Line[Vec2I]]]:
    """ Find contours in a 2D numpy array. """
    if array.dtype != bool:
        array = array > 0
    labeled_array, num_features = label(array)
    feature_lines: Dict[int, List[Line[Vec2I]]] = {
        i + 1: [] for i in range(num_features)
    }
    for (y, x) in np.argwhere(array):
        top_left, top_right = Vec2I(x, y), Vec2I(x + 1, y)
        bottom_right, bottom_left = Vec2I(x + 1, y + 1), Vec2I(x, y + 1)
        feature_id = labeled_array[y, x]
        feature_lines[feature_id].extend([
            Line(top_left, top_right),
            Line(top_right, bottom_right),
            Line(bottom_right, bottom_left),
            Line(bottom_left, top_left)
        ])
    
    contours = []
    for lines in feature_lines.values():
        non_dupe_lines = [line for line in lines if lines.count(line) == 1]
        # order the lines clockwise by tracing around the shape
        ordered_lines = [non_dupe_lines.pop(0)]
        while len(non_dupe_lines) > 0:
            for i, line in enumerate(non_dupe_lines):
                if line.start == ordered_lines[-1].end:
                    ordered_lines.append(line)
                    non_dupe_lines.pop(i)
                    break
        contours.append(ordered_lines)
    return contours
                