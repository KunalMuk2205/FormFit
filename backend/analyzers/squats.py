"""
Squat analyzer.
Tracks knee angle, hip angle, and knee-over-toe position.
State machine: STAND → UP → DOWN → UP (rep counted on DOWN→UP).
"""
import logging
import time
from datetime import datetime
import os
import pickle

import mediapipe as mp

from backend.utils.angles    import calculate_angle
from backend.utils.landmarks import get_landmark
from backend.utils.feedback  import visibility_hint
from backend.utils.dataset_logger import log_rep_features

mp_pose = mp.solutions.pose
logger  = logging.getLogger(__name__)

# Load ML model globally
try:
    _model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "squat_model.pkl")
    with open(_model_path, "rb") as f:
        squat_model = pickle.load(f)
    logger.info("Successfully loaded squat ML model.")
except Exception as e:
    logger.warning("Could not load squat ML model. Falling back to rule-based only. Error: %s", e)
    squat_model = None

SQUATS_SCHEMA = [
    "timestamp",
    "rep_duration_seconds",
    "min_knee_angle",
    "max_knee_angle",
    "avg_knee_angle",
    "min_hip_angle",
    "avg_hip_angle",
    "max_back_lean",
    "label_binary",
    "label_specific"
]


def analyze_squats(landmarks, w, h, state):
    """
    Mutates `state` in-place: updates count, stage, feedback, feedback_color,
    and angle_debug based on the current frame's pose landmarks.
    """
    try:
        lh = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value,      w, h)
        lk = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_KNEE.value,     w, h)
        la = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE.value,    w, h)
        ls = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value, w, h)

        knee_angle = calculate_angle(lh, lk, la)
        hip_angle  = calculate_angle(ls, lh, lk)

        state["angle_debug"] = {
            "knee": round(knee_angle),
            "hip":  round(hip_angle),
        }

        back_lean = abs(ls[0] - lh[0])

        # Manage dynamic ML feature buffers
        if "angle_history" not in state or not state["angle_history"]:
            state["angle_history"] = {"knee": [], "hip": [], "lean": []}
            state["rep_start_time"] = time.time()

        # Keep buffer fresh if they are just resting in the top position ("UP" in this state machine)
        if state["stage"] == "UP" and knee_angle > 160:
            state["angle_history"] = {"knee": [], "hip": [], "lean": []}
            state["rep_start_time"] = time.time()

        state["angle_history"]["knee"].append(knee_angle)
        state["angle_history"]["hip"].append(hip_angle)
        state["angle_history"]["lean"].append(back_lean)

        # Knee tracking: knee x > ankle x + 30px flags caving/forward lean
        knee_over_toe = lk[0] > la[0] + 30

        if state["stage"] == "STAND":
            if knee_angle > 160:
                state["stage"]          = "UP"
                state["feedback"]       = "Standing. Begin squat"
                state["feedback_color"] = "green"
            else:
                state["feedback"]       = "Stand up straight"
                state["feedback_color"] = "yellow"

        elif state["stage"] == "UP":
            if knee_angle < 100:
                state["stage"]          = "DOWN"
                
                # We need to capture the mistake when the user hits the bottom
                state["current_mistake"] = "knee_cave" if knee_over_toe else "none"
                
                state["feedback"]       = "Go back up!" if not knee_over_toe else "Knees caving in!"
                state["feedback_color"] = "cyan" if not knee_over_toe else "orange"

        elif state["stage"] == "DOWN":
            if knee_angle > 160:
                state["stage"]          = "UP"
                state["count"]         += 1
                
                mistake = state.get("current_mistake", "none")
                if mistake == "none":
                    state["good_reps"] = state.get("good_reps", 0) + 1
                    state["feedback"]       = "Rep {}! Good".format(state["count"])
                    state["feedback_color"] = "green"
                    label_binary = "good_form"
                    label_specific = "perfect"
                else:
                    state["bad_reps"] = state.get("bad_reps", 0) + 1
                    state["feedback"]       = "Rep {} — Knees caved".format(state["count"])
                    state["feedback_color"] = "orange"
                    label_binary = "bad_form"
                    label_specific = mistake
                    
                # ML DATA COLLECTION: Summarize and log features
                hist = state.get("angle_history", {"knee": [knee_angle], "hip": [hip_angle], "lean": [back_lean]})
                
                k_hist = hist["knee"] or [knee_angle]
                h_hist = hist["hip"] or [hip_angle]
                l_hist = hist["lean"] or [back_lean]
                
                rep_duration = round(time.time() - state.get("rep_start_time", time.time()), 2)
                
                features = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "rep_duration_seconds": rep_duration,
                    "min_knee_angle": round(min(k_hist), 2),
                    "max_knee_angle": round(max(k_hist), 2),
                    "avg_knee_angle": round(sum(k_hist) / len(k_hist), 2),
                    "min_hip_angle": round(min(h_hist), 2),
                    "avg_hip_angle": round(sum(h_hist) / len(h_hist), 2),
                    "max_back_lean": round(max(l_hist), 2),
                    "label_binary": label_binary,
                    "label_specific": label_specific
                }
                log_rep_features("squats", SQUATS_SCHEMA, features)
                
                # ── ML HYBRID LOGIC ──
                state["ml_prediction"] = None
                state["ml_confidence"] = None
                state["final_feedback"] = state["feedback"]

                if squat_model is not None:
                    try:
                        # Extract exact 7 features as expected by training model
                        X_live = [[
                            features["rep_duration_seconds"],
                            features["min_knee_angle"],
                            features["max_knee_angle"],
                            features["avg_knee_angle"],
                            features["min_hip_angle"],
                            features["avg_hip_angle"],
                            features["max_back_lean"]
                        ]]
                        
                        pred = squat_model.predict(X_live)[0]
                        proba = squat_model.predict_proba(X_live)[0]
                        conf = round(float(max(proba)), 2)
                        ml_pred = "good_form" if pred == 1 else "bad_form"
                        
                        state["ml_prediction"] = ml_pred
                        state["ml_confidence"] = conf
                        
                        # Apply hybrid overriding criteria:
                        if mistake == "none" and ml_pred == "bad_form":
                            # Rule-based GOOD but ML BAD -> Keep GOOD rep, add warning
                            state["final_feedback"] = f"{state['feedback']} (ML Warning: conf {conf})"
                            state["feedback_color"] = "yellow"
                            
                    except Exception as e:
                        logger.warning("ML prediction failed during squat rep: %s", e)

                # Reset buffers
                state["angle_history"] = {"knee": [], "hip": [], "lean": []}
                state["rep_start_time"] = time.time()
                state["current_mistake"] = "none"

    except Exception as e:
        logger.debug("analyze_squats failed: %s", e)
        state["feedback"]       = visibility_hint()
        state["feedback_color"] = "yellow"
