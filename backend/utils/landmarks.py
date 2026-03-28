"""
MediaPipe landmark extraction utility.
Converts normalised [0,1] landmark coordinates to pixel space.
"""


def get_landmark(landmarks, idx, w, h):
    """
    Return [x_px, y_px] for the landmark at index `idx`.
    `w` and `h` are the frame width and height in pixels.
    """
    lm = landmarks[idx]
    return [lm.x * w, lm.y * h]
