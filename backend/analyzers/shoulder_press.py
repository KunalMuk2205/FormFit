"""
Shoulder press analyzer.
Tracks left and right arm angles for full overhead extension.
State machine: DOWN → UP → DOWN (rep counted on UP→DOWN).
"""
import logging

import mediapipe as mp

from backend.utils.angles    import calculate_angle
from backend.utils.landmarks import get_landmark
from backend.utils.feedback  import visibility_hint

mp_pose = mp.solutions.pose
logger  = logging.getLogger(__name__)


def analyze_shoulder_press(landmarks, w, h, state):
    """
    Mutates `state` in-place: updates count, stage, feedback, feedback_color,
    and angle_debug based on the current frame's pose landmarks.
    """
    try:
        ls = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value,  w, h)
        le = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW.value,     w, h)
        lw = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_WRIST.value,     w, h)
        rs = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER.value, w, h)
        re = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_ELBOW.value,    w, h)
        rw = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_WRIST.value,    w, h)

        left_angle  = calculate_angle(ls, le, lw)
        right_angle = calculate_angle(rs, re, rw)
        avg = (left_angle + right_angle) / 2

        state["angle_debug"] = {
            "left_arm":  round(left_angle),
            "right_arm": round(right_angle),
        }

        # Lightweight live form score: penalise asymmetry and partial range
        asymmetry_pen = min(25, abs(left_angle - right_angle) / 2)
        lockout_pen   = max(0, min(20, (160 - avg) / 60 * 20)) if avg < 160 else 0
        instant       = max(0, 100 - asymmetry_pen - lockout_pen)
        state["form_score"] = 0.9 * state.get("form_score", 100) + 0.1 * instant

        if state["stage"] == "DOWN":
            if 80 < avg < 100:
                # Arms at ~90° = ready to press position
                state["feedback"]       = "Press up!"
                state["feedback_color"] = "green"
            if avg > 160:
                # Arms fully extended overhead
                state["stage"]          = "UP"
                state["feedback"]       = "Lower to shoulders"
                state["feedback_color"] = "cyan"

        elif state["stage"] == "UP":
            if avg < 100:
                state["stage"]          = "DOWN"
                state["count"]         += 1
                state["feedback"]       = "Rep {}! Good".format(state["count"])
                state["feedback_color"] = "green"

    except Exception as e:
        logger.debug("analyze_shoulder_press failed: %s", e)
        state["feedback"]       = visibility_hint()
        state["feedback_color"] = "yellow"
