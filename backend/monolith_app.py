from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import threading
import time

app = Flask(__name__)
CORS(app)

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# ── Global state per exercise ──────────────────────────────────────────────────
exercise_states = {
    "pushups": {
        "count": 0, "stage": "GET_READY", "feedback": "Get into plank position",
        "feedback_color": "yellow", "angle_debug": {}
    },
    "squats": {
        "count": 0, "stage": "STAND", "feedback": "Stand straight, feet shoulder-width",
        "feedback_color": "yellow", "angle_debug": {}
    },
    "bicep_curls": {
        "count": 0, "stage": "DOWN", "feedback": "Start with arms extended",
        "feedback_color": "green", "angle_debug": {}
    },
    "shoulder_press": {
        "count": 0, "stage": "DOWN", "feedback": "Hold weights at shoulder level",
        "feedback_color": "green", "angle_debug": {}
    },
}

_stream_lock = threading.Lock()   # serialises concurrent stream requests
_stop_event  = threading.Event()  # signals the running generator to exit its loop
cap = None

# ── Angle calculation ──────────────────────────────────────────────────────────
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(np.degrees(radians))
    return 360 - angle if angle > 180 else angle

def get_landmark(landmarks, idx, w, h):
    lm = landmarks[idx]
    return [lm.x * w, lm.y * h]

# ── Exercise analyzers ─────────────────────────────────────────────────────────
def analyze_pushups(landmarks, w, h, state):
    try:
        ls  = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value, w, h)
        le  = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW.value, w, h)
        lw  = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_WRIST.value, w, h)
        rs  = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER.value, w, h)
        re  = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_ELBOW.value, w, h)
        rw  = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_WRIST.value, w, h)
        lh  = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value, w, h)
        la  = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE.value, w, h)

        left_elbow_angle  = calculate_angle(ls, le, lw)
        right_elbow_angle = calculate_angle(rs, re, rw)
        back_angle        = calculate_angle(ls, lh, la)
        left_flare        = calculate_angle(lh, ls, le)

        avg_elbow = (left_elbow_angle + right_elbow_angle) / 2
        state["angle_debug"] = {"elbow": round(avg_elbow), "back": round(back_angle), "flare": round(left_flare)}

        form_ok = left_flare < 55

        if state["stage"] == "GET_READY":
            if back_angle > 160 and avg_elbow > 150:
                state["stage"] = "READY"
                state["feedback"] = "In position! Go down"
                state["feedback_color"] = "green"
            else:
                state["feedback"] = "Straighten your back & extend arms"
                state["feedback_color"] = "yellow"
        elif state["stage"] == "READY":
            if avg_elbow < 90:
                state["stage"] = "DOWN"
                state["feedback"] = "Push up!" if form_ok else "Tuck your elbows!"
                state["feedback_color"] = "cyan" if form_ok else "orange"
        elif state["stage"] == "DOWN":
            if avg_elbow > 150:
                state["stage"] = "READY"
                state["count"] += 1
                state["feedback"] = "Rep {}! Good".format(state['count']) if form_ok else "Tuck elbows next rep"
                state["feedback_color"] = "green" if form_ok else "orange"
    except Exception as e:
        state["feedback"] = "Adjust position"


def analyze_squats(landmarks, w, h, state):
    try:
        lh  = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value, w, h)
        lk  = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_KNEE.value, w, h)
        la  = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE.value, w, h)
        ls  = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value, w, h)

        knee_angle = calculate_angle(lh, lk, la)
        hip_angle  = calculate_angle(ls, lh, lk)

        state["angle_debug"] = {"knee": round(knee_angle), "hip": round(hip_angle)}

        knee_over_toe = lk[0] > la[0] + 30

        if state["stage"] == "STAND":
            if knee_angle > 160:
                state["stage"] = "UP"
                state["feedback"] = "Standing. Begin squat"
                state["feedback_color"] = "green"
            else:
                state["feedback"] = "Stand up straight"
                state["feedback_color"] = "yellow"
        elif state["stage"] == "UP":
            if knee_angle < 100:
                state["stage"] = "DOWN"
                msg = "Go back up!" if not knee_over_toe else "Knees caving in!"
                state["feedback"] = msg
                state["feedback_color"] = "cyan" if not knee_over_toe else "orange"
        elif state["stage"] == "DOWN":
            if knee_angle > 160:
                state["stage"] = "UP"
                state["count"] += 1
                state["feedback"] = "Rep {}! Good".format(state['count'])
                state["feedback_color"] = "green"
    except Exception as e:
        state["feedback"] = "Adjust position"


def analyze_bicep_curls(landmarks, w, h, state):
    try:
        ls = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value, w, h)
        le = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW.value, w, h)
        lw = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_WRIST.value, w, h)
        rs = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER.value, w, h)
        re = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_ELBOW.value, w, h)
        rw = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_WRIST.value, w, h)

        left_angle  = calculate_angle(ls, le, lw)
        right_angle = calculate_angle(rs, re, rw)
        avg = (left_angle + right_angle) / 2

        state["angle_debug"] = {"left_elbow": round(left_angle), "right_elbow": round(right_angle)}

        elbow_drift = abs(le[0] - ls[0]) > 60

        if state["stage"] == "DOWN":
            if avg > 150:
                state["feedback"] = "Curl up!"
                state["feedback_color"] = "green"
            if avg < 50:
                state["stage"] = "UP"
                state["feedback"] = "Lower slowly" if not elbow_drift else "Keep elbows tucked!"
                state["feedback_color"] = "cyan" if not elbow_drift else "orange"
        elif state["stage"] == "UP":
            if avg > 150:
                state["stage"] = "DOWN"
                state["count"] += 1
                state["feedback"] = "Rep {}! Good".format(state['count'])
                state["feedback_color"] = "green"
    except Exception as e:
        state["feedback"] = "Adjust position"


def analyze_shoulder_press(landmarks, w, h, state):
    try:
        ls = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value, w, h)
        le = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW.value, w, h)
        lw = get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_WRIST.value, w, h)
        rs = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER.value, w, h)
        re = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_ELBOW.value, w, h)
        rw = get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_WRIST.value, w, h)

        left_angle  = calculate_angle(ls, le, lw)
        right_angle = calculate_angle(rs, re, rw)
        avg = (left_angle + right_angle) / 2

        state["angle_debug"] = {"left_arm": round(left_angle), "right_arm": round(right_angle)}

        if state["stage"] == "DOWN":
            if 80 < avg < 100:
                state["feedback"] = "Press up!"
                state["feedback_color"] = "green"
            if avg > 160:
                state["stage"] = "UP"
                state["feedback"] = "Lower to shoulders"
                state["feedback_color"] = "cyan"
        elif state["stage"] == "UP":
            if avg < 100:
                state["stage"] = "DOWN"
                state["count"] += 1
                state["feedback"] = "Rep {}! Good".format(state['count'])
                state["feedback_color"] = "green"
    except Exception as e:
        state["feedback"] = "Adjust position"


ANALYZERS = {
    "pushups": analyze_pushups,
    "squats": analyze_squats,
    "bicep_curls": analyze_bicep_curls,
    "shoulder_press": analyze_shoulder_press,
}

COLOR_MAP = {
    "green": (0, 255, 100),
    "yellow": (0, 220, 255),
    "cyan": (255, 220, 0),
    "orange": (0, 140, 255),
    "red": (0, 60, 255),
}

# ── Frame generator ────────────────────────────────────────────────────────────
def generate_frames(exercise_id):
    """
    MJPEG generator for a single exercise stream.

    Safety guarantees:
    - Signals any existing stream to stop before acquiring the lock.
    - Holds _stream_lock for its entire lifetime → only one stream at a time.
    - Checks _stop_event each frame → exits cleanly on /api/stop or new stream.
    - Catches GeneratorExit → handles browser disconnect without traceback.
    - finally block → camera is ALWAYS released, even on crash.
    """
    global cap

    # Tell any currently-running stream to stop, then wait for its lock to free.
    _stop_event.set()
    with _stream_lock:
        _stop_event.clear()          # we now own the slot
        state = exercise_states[exercise_id]

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        try:
            with mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6) as pose:
                while not _stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame = cv2.flip(frame, 1)
                    h, w = frame.shape[:2]
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = pose.process(rgb)

                    # Draw pose
                    if results.pose_landmarks:
                        mp_drawing.draw_landmarks(
                            frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(0,255,180), thickness=3, circle_radius=5),
                            connection_drawing_spec=mp_drawing.DrawingSpec(color=(200,200,255), thickness=2)
                        )
                        ANALYZERS[exercise_id](results.pose_landmarks.landmark, w, h, state)

                    # ── Overlay UI ──
                    overlay = frame.copy()

                    # Top bar
                    cv2.rectangle(overlay, (0, 0), (w, 90), (15, 15, 25), -1)

                    # Rep counter box
                    cv2.rectangle(overlay, (20, 10), (200, 80), (30, 30, 50), -1)
                    cv2.rectangle(overlay, (20, 10), (200, 80), (0, 200, 120), 2)
                    cv2.putText(overlay, "REPS", (35, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 180), 1)
                    cv2.putText(overlay, str(state["count"]), (55, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 150), 3)

                    # Stage box
                    cv2.rectangle(overlay, (220, 10), (500, 80), (30, 30, 50), -1)
                    cv2.rectangle(overlay, (220, 10), (500, 80), (80, 80, 120), 2)
                    cv2.putText(overlay, "STAGE", (235, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 180), 1)
                    cv2.putText(overlay, state["stage"], (235, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 255), 2)

                    # Feedback bar
                    fb_color = COLOR_MAP.get(state["feedback_color"], (200, 200, 200))
                    cv2.rectangle(overlay, (0, h - 70), (w, h), (15, 15, 25), -1)
                    cv2.rectangle(overlay, (0, h - 70), (w, h), fb_color, 2)
                    cv2.putText(overlay, state["feedback"], (20, h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.95, fb_color, 2)

                    # Debug angles (bottom right)
                    x_dbg = w - 280
                    for i, (k, v) in enumerate(state["angle_debug"].items()):
                        cv2.putText(overlay, "{}: {}deg".format(k, v), (x_dbg, h - 75 - i * 25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120, 120, 160), 1)

                    cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)

                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        except GeneratorExit:
            pass   # client disconnected — exit cleanly without traceback
        finally:
            if cap is not None:
                cap.release()
                cap = None

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route('/api/video/<exercise_id>')
def video_feed(exercise_id):
    if exercise_id not in exercise_states:
        return jsonify({"error": "Unknown exercise"}), 404
    return Response(generate_frames(exercise_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/data/<exercise_id>')
def get_data(exercise_id):
    if exercise_id not in exercise_states:
        return jsonify({"error": "Unknown exercise"}), 404
    state = exercise_states[exercise_id]
    return jsonify({
        "count": state["count"],
        "stage": state["stage"],
        "feedback": state["feedback"],
        "feedback_color": state["feedback_color"],
        "angle_debug": state["angle_debug"],
    })

@app.route('/api/reset/<exercise_id>', methods=['POST'])
def reset(exercise_id):
    if exercise_id not in exercise_states:
        return jsonify({"error": "Unknown exercise"}), 404
    s = exercise_states[exercise_id]
    s["count"] = 0
    defaults = {
        "pushups":        ("GET_READY", "Get into plank position", "yellow"),
        "squats":         ("STAND",     "Stand straight, feet shoulder-width", "yellow"),
        "bicep_curls":    ("DOWN",      "Start with arms extended", "green"),
        "shoulder_press": ("DOWN",      "Hold weights at shoulder level", "green"),
    }
    s["stage"], s["feedback"], s["feedback_color"] = defaults[exercise_id]
    s["angle_debug"] = {}
    return jsonify({"status": "reset"})

@app.route('/api/stop', methods=['POST'])
def stop_stream():
    """Signals the running MJPEG generator to exit its loop.
    Called by the frontend when TrainerPage unmounts."""
    _stop_event.set()
    return jsonify({"status": "stopped"})

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
