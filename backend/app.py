"""
FormFit backend — entry point.

Run from the formfit_clean/ directory with:
    python -m backend.app

The `-m` flag ensures Python treats formfit_clean/ as the root of the package
tree, so all `from backend.*` imports resolve correctly.

Flask still serves on http://localhost:5000 — no change to the frontend proxy.
"""
import logging

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os

from backend.extensions import db
from backend.routes.exercise_routes import bp as exercise_bp
from backend.routes.history_routes import bp as history_bp
from backend.routes.auth_routes import bp as auth_bp

# Import models so SQLAlchemy knows about them before create_all()
from backend.models.user import User
from backend.models.workout import WorkoutSession, ExerciseResult



def create_app():
    """Application factory. Creates and configures the Flask app."""

    # Configure structured logging for all backend modules.
    # Format: timestamp [module.path] LEVEL: message
    # Technical details (tracebacks, landmark errors) stay here in the terminal.
    # The frontend never receives these — it only gets safe state["feedback"] strings.
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Silence noisy third-party loggers
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("mediapipe").setLevel(logging.WARNING)

    app = Flask(__name__)
    CORS(app)
    
    # Configure the SQLite database
    # This creates a file 'formfit.db' relative to the app instance directory
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "formfit.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Configure JWT
    app.config["JWT_SECRET_KEY"] = "formfit-super-secret-key-for-local-dev-only"  # In prod, use environment variable
    jwt = JWTManager(app)
    
    db.init_app(app)
    
    app.register_blueprint(exercise_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(auth_bp)
    
    # Ensure tables exist 
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    create_app().run(debug=True, host="0.0.0.0", port=5000, threaded=True)
