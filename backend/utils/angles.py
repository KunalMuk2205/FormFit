"""
Angle math utility.
Used by all exercise analyzers to measure joint angles from 2D coordinates.
"""
import numpy as np


def calculate_angle(a, b, c):
    """
    Return the interior angle (degrees) at vertex b, given three 2D points a, b, c.
    Result is always in the range [0, 180].
    """
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(np.degrees(radians))
    return 360 - angle if angle > 180 else angle

def get_smoothed_angle(key, raw_angle, state):
    """
    Applies Exponential Moving Average (EMA) to an angle to reduce jitter.
    Uses 'smoothing_alpha' from state to determine responsiveness vs. smoothness.
    """
    alpha = state.get("smoothing_alpha", 0.5)
    history = state.setdefault("smoothed_angles", {})
    
    if key not in history:
        history[key] = raw_angle
        return raw_angle
        
    smoothed = (alpha * raw_angle) + ((1.0 - alpha) * history[key])
    history[key] = smoothed
    return smoothed
