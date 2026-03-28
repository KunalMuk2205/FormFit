"""
Exercise API routes.
All five endpoints from the original app.py, registered as a Flask Blueprint.
Import this Blueprint and register it in backend/app.py.
"""
import logging

from flask import Blueprint, Response, jsonify

from backend.state.exercise_state import (
    exercise_states,
    generate_frames,
    reset_exercise,
    _stop_event,
)

bp     = Blueprint("exercises", __name__)
logger = logging.getLogger(__name__)


@bp.route("/api/video/<exercise_id>")
def video_feed(exercise_id):
    """Stream MJPEG frames for the given exercise."""
    if exercise_id not in exercise_states:
        logger.warning("video_feed 404: Unknown exercise '%s'", exercise_id)
        return jsonify({"error": "Unknown exercise"}), 404
    return Response(
        generate_frames(exercise_id),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@bp.route("/api/data/<exercise_id>")
def get_data(exercise_id):
    """Return current rep count, stage, feedback, and live angle debug values."""
    if exercise_id not in exercise_states:
        logger.warning("get_data 404: Unknown exercise '%s'", exercise_id)
        return jsonify({"error": "Unknown exercise"}), 404
    state = exercise_states[exercise_id]
    return jsonify({
        "count":          state["count"],
        "good_reps":      state.get("good_reps", 0),
        "bad_reps":       state.get("bad_reps", 0),
        "stage":          state["stage"],
        "feedback":       state["feedback"],
        "feedback_color": state["feedback_color"],
        "angle_debug":    state["angle_debug"],
        "form_score":     round(state["form_score"]),
        "ml_prediction":  state.get("ml_prediction"),
        "ml_confidence":  state.get("ml_confidence"),
        "final_feedback": state.get("final_feedback") or state["feedback"],
    })


@bp.route("/api/reset/<exercise_id>", methods=["POST"])
def reset(exercise_id):
    """Reset the session counters for the given exercise to defaults."""
    if exercise_id not in exercise_states:
        logger.warning("reset 404: Unknown exercise '%s'", exercise_id)
        return jsonify({"error": "Unknown exercise"}), 404
    reset_exercise(exercise_id)
    logger.info("Session reset for exercise: %s", exercise_id)
    return jsonify({"status": "reset"})


@bp.route("/api/stop", methods=["POST"])
def stop_stream():
    """
    Signal the running MJPEG generator to exit its loop.
    Called by the React frontend when TrainerPage unmounts.
    """
    _stop_event.set()
    logger.info("Stop requested via /api/stop API")
    return jsonify({"status": "stopped"})


@bp.route("/api/health")
def health():
    """Health check — used by the frontend connection indicator."""
    return jsonify({"status": "ok"})
