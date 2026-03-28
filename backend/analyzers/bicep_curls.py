"""
Bicep curl analyzer.
Tracks left and right elbow angles and detects elbow drift away from body.
State machine: DOWN → UP → DOWN (rep counted on UP→DOWN).
"""
import logging

import mediapipe as mp

from backend.utils.angles    import calculate_angle
from backend.utils.landmarks import get_landmark
from backend.utils.feedback  import visibility_hint

mp_pose = mp.solutions.pose
logger  = logging.getLogger(__name__)


def analyze_bicep_curls(landmarks, w, h, state):
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
            "left_elbow":  round(left_angle),
            "right_elbow": round(right_angle),
        }

        # Elbow drift: if left elbow is >60px away from shoulder horizontally,
        # the user is swinging rather than curling
        elbow_drift = abs(le[0] - ls[0]) > 60

        # Lightweight live form score
        drift_pen  = 30 if elbow_drift else 0
        range_pen  = max(0, min(20, (avg - 150) / 150 * 20)) if avg > 150 else 0
        instant    = max(0, 100 - drift_pen - range_pen)
        state["form_score"] = 0.9 * state.get("form_score", 100) + 0.1 * instant

        if state["stage"] == "DOWN":
            if avg > 150:
                state["feedback"]       = "Curl up!"
                state["feedback_color"] = "green"
            if avg < 50:
                state["stage"]          = "UP"
                state["feedback"]       = "Lower slowly" if not elbow_drift else "Keep elbows tucked!"
                state["feedback_color"] = "cyan" if not elbow_drift else "orange"

        elif state["stage"] == "UP":
            if avg > 150:
                state["stage"]          = "DOWN"
                state["count"]         += 1
                state["feedback"]       = "Rep {}! Good".format(state["count"])
                state["feedback_color"] = "green"

    except Exception as e:
        logger.debug("analyze_bicep_curls failed: %s", e)
        state["feedback"]       = visibility_hint()
        state["feedback_color"] = "yellow"
