import json
from datetime import datetime
from backend.extensions import db

class WorkoutSession(db.Model):
    __tablename__ = 'workout_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(120), nullable=True) # e.g., "Monday Chest Day"
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    
    # A single workout session can have multiple specific exercises performed within it
    exercises = db.relationship('ExerciseResult', backref='workout_session', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "exercises": [ex.to_dict() for ex in self.exercises]
        }


class ExerciseResult(db.Model):
    __tablename__ = 'exercise_results'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('workout_sessions.id'), nullable=False)
    
    exercise_name = db.Column(db.String(50), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    duration_seconds = db.Column(db.Integer, default=0)
    
    # Rep tracking
    total_reps = db.Column(db.Integer, default=0)
    good_reps = db.Column(db.Integer, default=0)
    bad_reps = db.Column(db.Integer, default=0)
    
    avg_form_score = db.Column(db.Float, default=0.0)
    
    # SQLite has a JSON type we can use with SQLAlchemy JSON or string
    # Storing array of issue strings e.g. ["elbow_flare", "shallow_depth"]
    common_mistakes = db.Column(db.JSON, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "exercise_name": self.exercise_name,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "total_reps": self.total_reps,
            "good_reps": self.good_reps,
            "bad_reps": self.bad_reps,
            "avg_form_score": round(self.avg_form_score, 1) if self.avg_form_score else 0.0,
            "common_mistakes": self.common_mistakes or []
        }
