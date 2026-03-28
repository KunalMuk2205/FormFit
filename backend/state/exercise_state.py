"""
Exercise state management and MJPEG stream control.

Responsibilities:
- Holds per-exercise mutable state (count, stage, feedback, angle_debug)
- Owns the stream primitives (_stream_lock, _stop_event, cap)
- Provides reset_exercise() for the reset route
- Provides generate_frames() — the MJPEG generator used by the video route
"""
import logging
import threading
import cv2
import mediapipe as mp

from backend.analyzers       import ANALYZERS
from backend.utils.drawing   import draw_ui_overlay

mp_pose    = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
logger     = logging.getLogger(__name__)


# ── Per-exercise mutable state ────────────────────────────────────────────────
# Each entry holds the live session data that both the stream and the
# /api/data route read from. Mutated by the analyzer functions each frame.
exercise_states = {
    "pushups": {
        "count": 0,
        "good_reps": 0,
        "bad_reps": 0,
        "stage": "GET_READY",
        "feedback": "Get into plank position",
        "feedback_color": "yellow",
        "angle_debug": {},
        "form_score": 100,
        "min_elbow_angle": 180,
        "smoothing_alpha": 0.4,
        "smoothed_angles": {},
        "rep_start_time": None,
        "angle_history": {},
        "ml_prediction": None,
        "ml_confidence": None,
        "final_feedback": None,
    },
    "squats": {
        "count": 0,
        "good_reps": 0,
        "bad_reps": 0,
        "stage": "STAND",
        "feedback": "Stand straight, feet shoulder-width",
        "feedback_color": "yellow",
        "angle_debug": {},
        "form_score": 100,
        "min_elbow_angle": 180,
        "smoothing_alpha": 0.4,
        "smoothed_angles": {},
        "rep_start_time": None,
        "angle_history": {},
        "ml_prediction": None,
        "ml_confidence": None,
        "final_feedback": None,
    },
    "bicep_curls": {
        "count": 0,
        "good_reps": 0,
        "bad_reps": 0,
        "stage": "DOWN",
        "feedback": "Start with arms extended",
        "feedback_color": "green",
        "angle_debug": {},
        "form_score": 100,
        "min_elbow_angle": 180,
        "smoothing_alpha": 0.4,
        "smoothed_angles": {},
        "ml_prediction": None,
        "ml_confidence": None,
        "final_feedback": None,
    },
    "shoulder_press": {
        "count": 0,
        "good_reps": 0,
        "bad_reps": 0,
        "stage": "DOWN",
        "feedback": "Hold weights at shoulder level",
        "feedback_color": "green",
        "angle_debug": {},
        "form_score": 100,
        "min_elbow_angle": 180,
        "smoothing_alpha": 0.4,
        "smoothed_angles": {},
        "ml_prediction": None,
        "ml_confidence": None,
        "final_feedback": None,
    },
}

# Default initial values per exercise — used by reset_exercise()
_DEFAULTS = {
    # format: (stage, feedback, color, min_elbow_angle, smoothing_alpha)
    "pushups":        ("GET_READY", "Get into plank position",         "yellow", 180, 0.4),
    "squats":         ("STAND",     "Stand straight, feet shoulder-width", "yellow", 180, 0.4),
    "bicep_curls":    ("DOWN",      "Start with arms extended",         "green",  180, 0.4),
    "shoulder_press": ("DOWN",      "Hold weights at shoulder level",   "green",  180, 0.4),
}


# ── Stream control primitives ─────────────────────────────────────────────────
_stream_lock = threading.Lock()   # ensures only one generator runs at a time
_stop_event  = threading.Event()  # signals the running generator to exit its loop
cap = None                        # active VideoCapture handle (None when idle)


# ── Reset helper ──────────────────────────────────────────────────────────────
def reset_exercise(exercise_id):
    """
    Reset the count, stage, feedback, and angle_debug for the given exercise
    back to its initial defaults. Safe to call while the stream is running.
    """
    s = exercise_states[exercise_id]
    s["count"] = 0
    s["good_reps"] = 0
    s["bad_reps"] = 0
    s["form_score"] = 100
    s["stage"], s["feedback"], s["feedback_color"], s["min_elbow_angle"], s["smoothing_alpha"] = _DEFAULTS[exercise_id]
    s["angle_debug"] = {}
    s["smoothed_angles"] = {}
    s["rep_start_time"] = None
    s["angle_history"] = {}
    s["ml_prediction"] = None
    s["ml_confidence"] = None
    s["final_feedback"] = None


# ── MJPEG generator ───────────────────────────────────────────────────────────
def generate_frames(exercise_id):
    """
    MJPEG generator for a single exercise stream.

    Safety guarantees:
    - Signals any existing stream to stop before acquiring _stream_lock.
    - Holds _stream_lock for its entire lifetime → only one stream at a time.
    - Checks _stop_event each frame → exits cleanly on /api/stop or new stream.
    - Catches GeneratorExit → handles browser disconnect without traceback.
    - finally block → camera is ALWAYS released, even on crash.
    """
    global cap

    # Tell any currently-running stream to stop, then wait for its lock to free
    _stop_event.set()
    with _stream_lock:
        _stop_event.clear()          # we now own the stream slot
        state = exercise_states[exercise_id]
        logger.info("Stream started: %s", exercise_id)

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        try:
            with mp_pose.Pose(
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6,
            ) as pose:
                while not _stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("Stream %s: camera read failed — stopping", exercise_id)
                        break

                    frame   = cv2.flip(frame, 1)
                    h, w    = frame.shape[:2]
                    rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = pose.process(rgb)

                    # Draw skeleton and run the exercise analyzer
                    if results.pose_landmarks:
                        mp_drawing.draw_landmarks(
                            frame,
                            results.pose_landmarks,
                            mp_pose.POSE_CONNECTIONS,
                            landmark_drawing_spec=mp_drawing.DrawingSpec(
                                color=(0, 255, 180), thickness=3, circle_radius=5
                            ),
                            connection_drawing_spec=mp_drawing.DrawingSpec(
                                color=(200, 200, 255), thickness=2
                            ),
                        )
                        ANALYZERS[exercise_id](
                            results.pose_landmarks.landmark, w, h, state
                        )

                    # Draw HUD overlay (rep counter, stage, feedback, angles)
                    draw_ui_overlay(frame, state)

                    # Encode and yield as MJPEG frame
                    _, buffer = cv2.imencode(
                        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60]
                    )
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + buffer.tobytes()
                        + b"\r\n"
                    )

        except GeneratorExit:
            logger.debug("Stream %s: client disconnected (GeneratorExit)", exercise_id)

        finally:
            if cap is not None:
                cap.release()
                cap = None
            logger.info("Stream stopped: %s", exercise_id)
