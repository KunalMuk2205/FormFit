import logging
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.extensions import db
from backend.models.user import User
from backend.models.workout import WorkoutSession, ExerciseResult
from datetime import datetime

logger = logging.getLogger(__name__)
bp = Blueprint("history", __name__, url_prefix="/api/history")


@bp.route("/", methods=["GET"])
@jwt_required()
def get_all_history():
    """
    Fetch all workout sessions exclusively for the currently authenticated user.
    """
    user_id = get_jwt_identity()
    sessions = WorkoutSession.query.filter_by(user_id=user_id).order_by(WorkoutSession.start_time.desc()).all()
    
    return jsonify([session.to_dict() for session in sessions]), 200


@bp.route("/save", methods=["POST"])
@jwt_required()
def save_exercise_result():
    """
    Saves the final stats of an exercise securely linked to the logged-in user.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    user_id = get_jwt_identity()

    now = datetime.utcnow()
    new_session = WorkoutSession(
        user_id=user_id,
        title=f"Session - {now.strftime('%b %d, %Y')}",
        start_time=now,
        end_time=now  # Since we are just persisting the end stats
    )
    
    db.session.add(new_session)
    db.session.commit() # Commit to get the new_session.id

    new_result = ExerciseResult(
        session_id=new_session.id,
        exercise_name=data.get("exercise_name"),
        duration_seconds=data.get("duration_seconds", 0),
        total_reps=data.get("total_reps", 0),
        good_reps=data.get("good_reps", 0),
        bad_reps=data.get("bad_reps", 0),
        avg_form_score=data.get("avg_form_score", 0.0),
        common_mistakes=data.get("common_mistakes", [])
    )
    
    db.session.add(new_result)
    db.session.commit()

    logger.info("Saved new exercise result to database (Session ID: %s)", new_session.id)
    return jsonify({"message": "Saved successfully", "session": new_session.to_dict()}), 201
