"""
Frame overlay drawing utilities.
Extracted from the generate_frames() inline block in the original app.py.
COLOR_MAP translates feedback_color string names to BGR tuples for OpenCV.
"""
import cv2


# BGR colour values for each feedback state
COLOR_MAP = {
    "green":  (0, 255, 100),
    "yellow": (0, 220, 255),
    "cyan":   (255, 220, 0),
    "orange": (0, 140, 255),
    "red":    (0, 60, 255),
}


def draw_ui_overlay(frame, state):
    """
    Draw the HUD (rep counter, stage box, feedback bar, angle debug) onto `frame` in-place.
    Uses a semi-transparent overlay blended with cv2.addWeighted so the video
    feed shows through beneath the UI elements.

    Args:
        frame: BGR numpy array — modified in-place.
        state: exercise state dict with keys count, stage, feedback,
               feedback_color, angle_debug.
    """
    overlay = frame.copy()
    h, w = frame.shape[:2]

    # ── Top bar background ──────────────────────────────────────────────
    cv2.rectangle(overlay, (0, 0), (w, 90), (15, 15, 25), -1)

    # ── Rep counter box ─────────────────────────────────────────────────
    cv2.rectangle(overlay, (20, 10), (200, 80), (30, 30, 50), -1)
    cv2.rectangle(overlay, (20, 10), (200, 80), (0, 200, 120), 2)
    cv2.putText(overlay, "REPS",
                (35, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 180), 1)
    cv2.putText(overlay, str(state["count"]),
                (55, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 150), 3)

    # ── Stage box ───────────────────────────────────────────────────────
    cv2.rectangle(overlay, (220, 10), (500, 80), (30, 30, 50), -1)
    cv2.rectangle(overlay, (220, 10), (500, 80), (80, 80, 120), 2)
    cv2.putText(overlay, "STAGE",
                (235, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 180), 1)
    cv2.putText(overlay, state["stage"],
                (235, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 255), 2)

    # ── Feedback bar (bottom) ────────────────────────────────────────────
    fb_color = COLOR_MAP.get(state["feedback_color"], (200, 200, 200))
    cv2.rectangle(overlay, (0, h - 70), (w, h), (15, 15, 25), -1)
    cv2.rectangle(overlay, (0, h - 70), (w, h), fb_color, 2)
    
    fb_text = state.get("final_feedback") or state.get("feedback", "")
    cv2.putText(overlay, str(fb_text),
                (20, h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.95, fb_color, 2)

    # ── Angle debug values (bottom-right) ───────────────────────────────
    x_dbg = w - 280
    for i, (k, v) in enumerate(state["angle_debug"].items()):
        cv2.putText(overlay, "{}: {}deg".format(k, v),
                    (x_dbg, h - 75 - i * 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120, 120, 160), 1)

    # Blend overlay onto frame (90% overlay, 10% original)
    cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)
