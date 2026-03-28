"""
Push-up analyzer.
Tracks elbow angle, back/hip alignment, elbow flare, and neck alignment.
State machine: GET_READY → READY → DOWN → READY (rep counted on DOWN→READY).
"""
import logging
import time
from datetime import datetime
import os
import pickle

import mediapipe as mp

from backend.utils.angles    import calculate_angle, get_smoothed_angle
from backend.utils.landmarks import get_landmark
from backend.utils.feedback  import visibility_hint
from backend.utils.dataset_logger import log_rep_features

mp_pose = mp.solutions.pose
logger  = logging.getLogger(__name__)

# Load ML model globally
try:
    _model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "pushup_model.pkl")
    with open(_model_path, "rb") as f:
        pushup_model = pickle.load(f)
    logger.info("Successfully loaded pushup ML model.")
except Exception as e:
    logger.warning("Could not load pushup ML model. Falling back to rule-based only. Error: %s", e)
    pushup_model = None

PUSHUPS_SCHEMA = [
    "timestamp",
    "rep_duration_seconds",
    "min_elbow_angle",
    "max_elbow_angle",
    "avg_elbow_angle",
    "min_back_angle",
    "avg_back_angle",
    "max_flare_angle",
    "min_neck_angle",
    "label_binary",
    "label_specific"
]

# ── TUNING THRESHOLDS ─────────────────────────────────────────────────────────
# These variables control exactly how strict the form assessment is.
THRESHOLDS = {
    # 1. Back/Hip Posture
    "back_straight": 160,    # Ideal straight line
    "back_sag": 130,         # Maximum penalty applied here
    
    # 2. Elbow Flare
    "flare_ideal": 55,       # Ideal tucked angle
    "flare_wide": 85,        # Maximum penalty applied here
    
    # 3. Movement Lockout
    "lockout_ideal": 150,    # Arms fully extended
    "lockout_bent": 130,     # Maximum penalty applied here
    
    # 4. Movement Depth
    "depth_ideal": 90,       # Hit at least 90°
    "depth_shallow": 120,    # Maximum penalty applied here
    
    # 5. Neck/Head Alignment
    "neck_straight": 160,    # Ear/Shoulder/Hip inline
    "neck_craned": 140,      # Craning forward
}


def calculate_penalty(value, ideal, worst, max_pts):
    """
    Computes a proportional penalty based on how far 'value' is from 'ideal'.
    If 'value' is on the "good" side of 'ideal', returns 0.
    If 'value' is at or beyond 'worst', returns 'max_pts'.
    """
    if ideal > worst:
        # e.g., back_angle: 160 -> 130
        if value >= ideal: return 0
        if value <= worst: return max_pts
        diff_total  = ideal - worst
        diff_actual = ideal - value
    else:
        # e.g., flare: 55 -> 85
        if value <= ideal: return 0
        if value >= worst: return max_pts
        diff_total  = worst - ideal
        diff_actual = value - ideal
        
    fraction = diff_actual / diff_total
    return max_pts * fraction


def analyze_pushups(landmarks, w, h, state):
    """
    Mutates `state` in-place: updates count, stage, feedback, feedback_color,
    and angle_debug based on the current frame's pose landmarks.
    """
    try:
        # Extract the specific landmarks we care about
        le_ear = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_EAR.value,       w, h)
        ls     = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value,  w, h)
        le     = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW.value,     w, h)
        lw     = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_WRIST.value,     w, h)
        rs     = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER.value, w, h)
        re     = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_ELBOW.value,    w, h)
        rw     = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_WRIST.value,    w, h)
        lh     = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value,       w, h)
        la     = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE.value,     w, h)

        # Calculate angles and apply exponential smoothing
        left_elbow_angle  = get_smoothed_angle("left_elbow", calculate_angle(ls, le, lw), state)
        right_elbow_angle = get_smoothed_angle("right_elbow", calculate_angle(rs, re, rw), state)
        avg_elbow         = (left_elbow_angle + right_elbow_angle) / 2
        
        back_angle        = get_smoothed_angle("back", calculate_angle(ls, lh, la), state)      # hip-shoulder-ankle alignment
        left_flare        = get_smoothed_angle("left_flare", calculate_angle(lh, ls, le), state) # elbow flare from torso
        neck_angle        = get_smoothed_angle("neck", calculate_angle(le_ear, ls, lh), state)   # ear-shoulder-hip alignment

        # Add all tracking info to the angle_debug output for dev mode
        state["angle_debug"] = {
            "elbow": round(avg_elbow),
            "back":  round(back_angle),
            "flare": round(left_flare),
            "neck":  round(neck_angle),
        }

        # Manage dynamic ML feature buffers
        if "angle_history" not in state or not state["angle_history"]:
            state["angle_history"] = {"elbow": [], "back": [], "flare": [], "neck": []}
            state["rep_start_time"] = time.time()

        # Keep buffer fresh if they are just resting in the top position
        if state["stage"] == "READY" and avg_elbow > 160:
            state["angle_history"] = {"elbow": [], "back": [], "flare": [], "neck": []}
            state["rep_start_time"] = time.time()

        # Append live features per frame
        state["angle_history"]["elbow"].append(avg_elbow)
        state["angle_history"]["back"].append(back_angle)
        state["angle_history"]["flare"].append(left_flare)
        state["angle_history"]["neck"].append(neck_angle)

        # ── 1. LIVE FORM SCORING ──
        back_pen  = calculate_penalty(back_angle, THRESHOLDS["back_straight"], THRESHOLDS["back_sag"], 25)
        flare_pen = calculate_penalty(left_flare, THRESHOLDS["flare_ideal"],   THRESHOLDS["flare_wide"], 20)
        neck_pen  = calculate_penalty(neck_angle, THRESHOLDS["neck_straight"], THRESHOLDS["neck_craned"], 15)
        
        # Lockout is strictly penalized when resting between reps.
        lockout_pen = 0
        if state["stage"] in ("READY", "GET_READY"):
            lockout_pen = calculate_penalty(avg_elbow, THRESHOLDS["lockout_ideal"], THRESHOLDS["lockout_bent"], 20)
            
        # Depth penalty evaluates how low the user got during the rep phase
        depth_pen = 0
        min_e = state.get("min_elbow_angle", 180)
        # Only apply depth penalty if they have actually started a rep descent
        if min_e < 180:
             depth_pen = calculate_penalty(min_e, THRESHOLDS["depth_ideal"], THRESHOLDS["depth_shallow"], 20)

        # Assemble and smooth instantaneous score
        instant_score = max(0, 100 - back_pen - flare_pen - neck_pen - lockout_pen - depth_pen)
        
        old_score = state.get("form_score", 100)
        state["form_score"] = (0.9 * old_score) + (0.1 * instant_score)
        
        
        # ── 2. STATE MACHINE & REP COUNTING ──
        # Track elbow depth going down
        if state["stage"] == "DOWN":
            state["min_elbow_angle"] = min(state["min_elbow_angle"], avg_elbow)

        # Strict rep qualification checks
        flare_ok = left_flare < THRESHOLDS["flare_ideal"]
        depth_ok = state.get("min_elbow_angle", 180) < THRESHOLDS["depth_ideal"]
        form_ok  = flare_ok and depth_ok

        if state["stage"] == "GET_READY":
            state["min_elbow_angle"] = 180  # ensure memory is wiped
            if back_angle > 150 and avg_elbow > 140:
                state["stage"]          = "READY"
                state["feedback"]       = "In position! Go down"
                state["feedback_color"] = "green"
            else:
                state["feedback"]       = "Straighten back & look forward"
                state["feedback_color"] = "yellow"

        elif state["stage"] == "READY":
            if avg_elbow < 90:
                state["stage"]          = "DOWN"
                state["feedback"]       = "Push up!" if flare_ok else "Tuck your elbows!"
                state["feedback_color"] = "cyan" if flare_ok else "orange"

        elif state["stage"] == "DOWN":
            if avg_elbow > 150:
                state["stage"]    = "READY"
                state["count"]   += 1
                
                # Check metrics to award a good or bad rep
                if form_ok:
                    state["good_reps"] = state.get("good_reps", 0) + 1
                    state["feedback"] = "Rep {}! Perfect form".format(state["count"])
                    state["feedback_color"] = "green"
                    label_binary = "good_form"
                    label_specific = "perfect"
                else:
                    state["bad_reps"] = state.get("bad_reps", 0) + 1
                    if not depth_ok:
                        state["feedback"] = "Rep {} — Go lower next time".format(state["count"])
                        label_specific = "shallow_depth"
                    else:
                        state["feedback"] = "Rep {} — Tuck your elbows".format(state["count"])
                        label_specific = "elbow_flare"
                    state["feedback_color"] = "orange"
                    label_binary = "bad_form"
                    
                # ML DATA COLLECTION: Summarize and log features
                hist = state.get("angle_history", {"elbow": [avg_elbow], "back": [back_angle], "flare": [left_flare], "neck": [neck_angle]})
                
                e_hist = hist["elbow"] or [avg_elbow]
                b_hist = hist["back"] or [back_angle]
                f_hist = hist["flare"] or [left_flare]
                n_hist = hist["neck"] or [neck_angle]
                
                rep_duration = round(time.time() - state.get("rep_start_time", time.time()), 2)
                
                features = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "rep_duration_seconds": rep_duration,
                    "min_elbow_angle": round(min(e_hist), 2),
                    "max_elbow_angle": round(max(e_hist), 2),
                    "avg_elbow_angle": round(sum(e_hist) / len(e_hist), 2),
                    "min_back_angle": round(min(b_hist), 2),
                    "avg_back_angle": round(sum(b_hist) / len(b_hist), 2),
                    "max_flare_angle": round(max(f_hist), 2),
                    "min_neck_angle": round(min(n_hist), 2),
                    "label_binary": label_binary,
                    "label_specific": label_specific
                }
                log_rep_features("pushups", PUSHUPS_SCHEMA, features)
                    
                # ── ML HYBRID LOGIC ──
                state["ml_prediction"] = None
                state["ml_confidence"] = None
                state["final_feedback"] = state["feedback"]

                if pushup_model is not None:
                    try:
                        # Extract the exact 8 features in the order expected by the model
                        X_live = [[
                            features["rep_duration_seconds"],
                            features["min_elbow_angle"],
                            features["max_elbow_angle"],
                            features["avg_elbow_angle"],
                            features["min_back_angle"],
                            features["avg_back_angle"],
                            features["max_flare_angle"],
                            features["min_neck_angle"]
                        ]]
                        
                        pred = pushup_model.predict(X_live)[0]
                        proba = pushup_model.predict_proba(X_live)[0]
                        conf = round(float(max(proba)), 2)
                        ml_pred = "good_form" if pred == 1 else "bad_form"
                        
                        state["ml_prediction"] = ml_pred
                        state["ml_confidence"] = conf
                        
                        # Apply hybrid overriding criteria:
                        if form_ok and ml_pred == "bad_form":
                            # Rule-based GOOD but ML BAD -> Keep GOOD rep, add warning
                            state["final_feedback"] = f"{state['feedback']} (ML Warning: conf {conf})"
                            state["feedback_color"] = "yellow"
                            
                    except Exception as e:
                        logger.warning("ML prediction failed during rep: %s", e)

                # Wipe depth memory for the next rep
                state["min_elbow_angle"] = 180
                state["angle_history"] = {"elbow": [], "back": [], "flare": [], "neck": []}
                state["rep_start_time"] = time.time()

    except Exception as e:
        # Technical failures (missing landmarks)
        logger.debug("analyze_pushups failed: %s", e)
        state["feedback"]       = visibility_hint()
        state["feedback_color"] = "yellow"
