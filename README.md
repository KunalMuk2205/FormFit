<div align="center">

# ⚡ FormFit

### AI-Powered Real-Time Exercise Form Trainer

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![React](https://img.shields.io/badge/React-18.x-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10-0097A7?style=for-the-badge&logo=google&logoColor=white)](https://mediapipe.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)

**FormFit uses your webcam + Google's MediaPipe to detect 33 body landmarks every frame, measure joint angles with trigonometry, count your reps, score your form out of 100, and speak corrective feedback in real time — all running locally on your machine.**

[Features](#-features) · [Demo](#-exercises--what-gets-tracked) · [Setup](#-quick-start) · [Architecture](#-architecture) · [ML Pipeline](#-machine-learning-pipeline) · [API Reference](#-api-reference)

---

![FormFit Banner](https://via.placeholder.com/900x400/0D0D14/00FF87?text=FormFit+%E2%80%94+AI+Exercise+Form+Trainer)

</div>

---

## ✨ Features

- 🎥 **Real-time pose detection** — MediaPipe BlazePose detects 33 body landmarks at up to 60fps
- 📐 **Joint angle measurement** — arctan2 trigonometry measures elbow, knee, hip, and shoulder angles every frame
- 🔢 **Automatic rep counting** — State machine logic counts only complete, valid movement cycles
- 💯 **Live form score (0–100)** — Penalty-based scoring across 5 form dimensions, updated every frame
- 🤖 **Hybrid ML validation** — RandomForest models trained on real session data provide a second-opinion form check after every rep
- 🔊 **Voice feedback** — Browser Web Speech API speaks corrective cues out loud with anti-stutter logic
- 👤 **User accounts** — JWT authentication + bcrypt password hashing
- 📊 **Performance dashboard** — Line charts, pie charts, KPI cards showing progress over time
- 📅 **Workout history** — All completed sessions saved to SQLite database
- 🔒 **Fully local** — No video or biometric data ever leaves your machine

---

## 🏋️ Exercises & What Gets Tracked

| Exercise | Landmarks Used | Form Checks | Has ML Model |
|---|---|---|---|
| **Push-Ups** | Shoulder, Elbow, Wrist, Hip, Ankle, Ear | Back sag · Elbow flare · Depth · Neck alignment · Lockout | ✅ Yes |
| **Squats** | Hip, Knee, Ankle, Shoulder | Knee angle · Hip angle · Knee-over-toe caving | ✅ Yes |
| **Bicep Curls** | Shoulder, Elbow, Wrist (both sides) | Elbow drift away from body | ❌ Rule-based only |
| **Shoulder Press** | Shoulder, Elbow, Wrist (both sides) | Full overhead extension · Left/right asymmetry | ❌ Rule-based only |

### Push-Up Form Score Breakdown

The push-up analyzer is the most advanced. Every frame, up to **100 points** are awarded minus proportional penalties:

| Check | Max Penalty | What triggers it |
|---|---|---|
| Back sag | 25 pts | back angle < 160° (ideal) → 130° (worst) |
| Elbow flare | 20 pts | elbow flare > 55° (ideal) → 85° (worst) |
| Lockout | 20 pts | arms not fully extended at top (< 150°) |
| Depth | 20 pts | elbow angle at bottom > 90° (not going low enough) |
| Neck alignment | 15 pts | ear-shoulder-hip angle < 160° (head dropped) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│      BROWSER  (port 3000)       │         │    FLASK SERVER  (port 5000)    │
│                                 │         │                                 │
│  ┌──────────────────────────┐   │◄───────►│  ┌──────────────────────────┐  │
│  │      HomePage.js         │   │         │  │   exercise_routes.py     │  │
│  │  Exercise selection +    │   │         │  │  /api/video  /api/data   │  │
│  │  particle canvas bg      │   │         │  │  /api/reset  /api/stop   │  │
│  └──────────────────────────┘   │         │  └──────────────────────────┘  │
│  ┌──────────────────────────┐   │         │  ┌──────────────────────────┐  │
│  │      TrainerPage.js      │   │ MJPEG   │  │    exercise_state.py     │  │
│  │  Live video · Reps       │◄──┼─────────┤  │  generate_frames() loop  │  │
│  │  Voice · Form score      │   │ JSON    │  │  OpenCV · MediaPipe      │  │
│  │  Mistakes · Save flow    │──►┼─────────►  │  Analyzers · draw_ui     │  │
│  └──────────────────────────┘   │         │  └──────────────────────────┘  │
│  ┌──────────────────────────┐   │         │  ┌──────────────────────────┐  │
│  │  HistoryPage.js          │   │  JWT    │  │     auth_routes.py       │  │
│  │  DashboardPage.js        │◄──┼─────────►  │  /api/auth/register      │  │
│  │  AuthPage.js             │   │         │  │  /api/auth/login         │  │
│  └──────────────────────────┘   │         │  └──────────────────────────┘  │
│  ┌──────────────────────────┐   │         │  ┌──────────────────────────┐  │
│  │     AuthContext.js       │   │  REST   │  │    history_routes.py     │  │
│  │  Global JWT token store  │◄──┼─────────►  │  /api/history/ (GET)     │  │
│  └──────────────────────────┘   │         │  │  /api/history/save (POST)│  │
└─────────────────────────────────┘         │  └──────────────────────────┘  │
                                            │                                 │
                                            │  SQLite DB · ML Models (.pkl)  │
                                            │  Webcam · MediaPipe · NumPy    │
                                            └─────────────────────────────────┘
```

---

## 📁 Project Structure

```
FormFit/
│
├── app.py                          # V1 — original all-in-one server (reference)
├── requirements.txt
├── package.json
│
├── backend/                        # V2 — modular production backend
│   ├── app.py                      # Entry point: create_app() factory
│   ├── extensions.py               # db = SQLAlchemy() singleton
│   │
│   ├── analyzers/                  # One file per exercise
│   │   ├── pushups.py              # State machine + 5 penalties + ML + CSV logging
│   │   ├── squats.py               # State machine + knee-cave check + ML
│   │   ├── bicep_curls.py          # State machine + elbow drift check
│   │   └── shoulder_press.py       # State machine + asymmetry penalty
│   │
│   ├── utils/
│   │   ├── angles.py               # calculate_angle() + get_smoothed_angle() (EMA)
│   │   ├── landmarks.py            # get_landmark() — 0–1 coords → pixel coords
│   │   ├── drawing.py              # draw_ui_overlay() — paints HUD onto frame
│   │   ├── feedback.py             # visibility_hint() — friendly fallback messages
│   │   └── dataset_logger.py       # log_rep_features() — writes CSV rows for ML
│   │
│   ├── state/
│   │   └── exercise_state.py       # exercise_states dict + generate_frames() + reset
│   │
│   ├── routes/
│   │   ├── exercise_routes.py      # /api/video, /api/data, /api/reset, /api/stop
│   │   ├── auth_routes.py          # /api/auth/register, /api/auth/login, /api/auth/me
│   │   └── history_routes.py       # /api/history/ GET + /api/history/save POST
│   │
│   ├── models/
│   │   ├── user.py                 # User table — id, username, password_hash
│   │   └── workout.py              # WorkoutSession + ExerciseResult tables
│   │
│   ├── ml/
│   │   ├── train_model.py          # Offline training: CSV → RandomForest → .pkl
│   │   ├── pushup_model.pkl        # Pre-trained push-up classifier
│   │   └── squat_model.pkl         # Pre-trained squat classifier
│   │
│   └── dataset/
│       ├── pushups.csv             # Auto-logged rep features (grows as you exercise)
│       └── squats.csv
│
├── src/                            # React frontend
│   ├── index.js                    # Mounts <App/> onto index.html
│   ├── App.js                      # BrowserRouter with 5 routes + AuthProvider
│   │
│   ├── context/
│   │   └── AuthContext.js          # Global token + user + login/register/logout
│   │
│   ├── pages/
│   │   ├── HomePage.js             # Exercise selection + particle animation
│   │   ├── TrainerPage.js          # Live workout: video + polling + voice + save
│   │   ├── AuthPage.js             # Login / register + pending_save recovery
│   │   ├── HistoryPage.js          # Past workout session cards
│   │   └── DashboardPage.js        # Recharts line + pie charts + KPI cards
│   │
│   └── components/
│       └── SessionSummary.js       # End-of-session modal + mistake analysis
│
└── public/
    └── index.html                  # Single HTML shell — React injects here
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- A webcam

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/FormFit.git
cd FormFit
```

### 2. Backend setup

```bash
# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the backend

```bash
# From the project root
python -m backend.app
```

Flask will start at **http://localhost:5000**

> **Note:** Use `python -m backend.app` (not `python backend/app.py`) so Python resolves the `from backend.*` imports correctly.

### 4. Frontend setup

Open a **new terminal** in the project root:

```bash
npm install
npm start
```

React will open at **http://localhost:3000**

> The `proxy` field in `package.json` automatically forwards all `/api/...` calls to port 5000 — no CORS configuration needed during development.

### 5. Start training

1. Open **http://localhost:3000**
2. Click any exercise card
3. Follow the camera positioning instructions
4. Click **Start Workout**
5. Exercise — FormFit will count reps and speak corrective feedback

---

## 🧠 How It Works

### The Frame Pipeline

Every single frame (~30–60 per second) goes through this pipeline:

```
Webcam frame
    │
    ▼
cv2.flip(frame, 1)          ← Mirror so it feels natural
    │
    ▼
BGR → RGB convert            ← MediaPipe needs RGB; OpenCV gives BGR
    │
    ▼
pose.process(rgb)            ← MediaPipe AI: 33 landmark (x, y, z, visibility) coords
    │
    ├── No landmarks? → show visibility hint ("Move back from camera")
    │
    ▼
mp_drawing.draw_landmarks()  ← Draws green dots + white skeleton on frame
    │
    ▼
ANALYZERS[exercise_id]()     ← Updates count, stage, feedback, form_score in state dict
    │
    ▼
draw_ui_overlay()            ← Paints REPS box + STAGE label + feedback bar onto frame
    │
    ▼
cv2.imencode('.jpg', frame)  ← Compress to JPEG (quality 60)
    │
    ▼
yield MJPEG frame            ← Push to browser via multipart/x-mixed-replace stream
    │
    └─────────────────────────── next frame ↑
```

### Angle Calculation

All exercise logic is built on one mathematical function:

```python
def calculate_angle(a, b, c):
    """
    Returns the interior angle (degrees) at vertex B, given points A, B, C.
    Uses arctan2 to find the direction of each arm, then subtracts.
    Result is always in [0, 180].
    """
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(np.degrees(radians))
    return 360 - angle if angle > 180 else angle
```

**Example:** For a push-up, A = shoulder, B = elbow, C = wrist. The function returns the angle at the elbow — ~160° when arms are extended, ~70° at the bottom of a rep.

### EMA Smoothing

Raw landmark positions jitter between frames even when you're perfectly still. Without smoothing this causes false rep counts.

```python
def get_smoothed_angle(key, raw_angle, state):
    alpha = state.get("smoothing_alpha", 0.5)  # 0.4 in this project
    smoothed = (alpha * raw_angle) + ((1 - alpha) * previous)
    return smoothed
```

With `alpha = 0.4`: 40% new reading + 60% previous → stable angles that respond to real movement and ignore sensor noise.

### State Machines

Each exercise uses a state machine that only counts reps when the full movement cycle is completed in order:

**Push-Ups:**
```
GET_READY ──(back>150° AND elbow>140°)──► READY ──(elbow<90°)──► DOWN ──(elbow>150°)──► READY + count++
                                            ▲                                                    │
                                            └────────────────── loop back ────────────────────────┘
```

**Squats:**
```
STAND ──(knee>160°)──► UP ──(knee<100°)──► DOWN ──(knee>160°)──► UP + count++
                        ▲                                              │
                        └───────────────── loop back ──────────────────┘
```

**Bicep Curls / Shoulder Press:**
```
DOWN ──(avg<50°)──► UP ──(avg>150°)──► DOWN + count++
 ▲                                           │
 └──────────────── loop back ────────────────┘
```

---

## 🤖 Machine Learning Pipeline

FormFit uses a **hybrid AI approach**: rule-based state machines are the primary counter, and trained RandomForest models act as a second-opinion validator after every rep.

### Data Collection

Every completed rep automatically logs a row to a CSV file:

```
# backend/dataset/pushups.csv (auto-generated)
timestamp, rep_duration_seconds, min_elbow_angle, max_elbow_angle, avg_elbow_angle,
min_back_angle, avg_back_angle, max_flare_angle, min_neck_angle, label_binary, label_specific
```

Labels are assigned automatically by the rule-based logic (`good_form` / `bad_form`).

### Training

Once you have enough data (recommended: 100+ reps), retrain the model:

```bash
python -m backend.ml.train_model
```

This reads the CSV, trains a `RandomForestClassifier(n_estimators=100)` with an 80/20 train/test split, prints accuracy and feature importances, and saves the new model as a `.pkl` file.

### Hybrid Prediction Logic

After each rep completes:

```
Rule-based result  │  ML result  │  Outcome
───────────────────┼─────────────┼────────────────────────────────────────────
good_form          │  good_form  │  "Rep 3! Perfect form"  ✅
good_form          │  bad_form   │  "Rep 3! Perfect form (ML Warning: conf 0.78)"  ⚠️
bad_form           │  any        │  "Rep 3 — Go lower next time"  ❌
```

The ML model **never overrides** the rule-based counter — it only adds a warning when it disagrees with a "good" classification.

---

## 🔌 API Reference

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/video/<exercise_id>` | GET | ❌ | MJPEG video stream with skeleton + HUD overlay |
| `/api/data/<exercise_id>` | GET | ❌ | JSON: count, good_reps, bad_reps, stage, feedback, form_score, ml_prediction, ml_confidence |
| `/api/reset/<exercise_id>` | POST | ❌ | Reset session counters to defaults |
| `/api/stop` | POST | ❌ | Signal MJPEG generator to stop and release camera |
| `/api/health` | GET | ❌ | Health check — returns `{"status": "ok"}` |
| `/api/auth/register` | POST | ❌ | Create user with bcrypt-hashed password |
| `/api/auth/login` | POST | ❌ | Verify credentials, returns JWT access token |
| `/api/auth/me` | GET | ✅ JWT | Get current user info from token |
| `/api/history/` | GET | ✅ JWT | Fetch all workout sessions for logged-in user |
| `/api/history/save` | POST | ✅ JWT | Save completed exercise result to database |

**Exercise IDs:** `pushups` · `squats` · `bicep_curls` · `shoulder_press`

### Example: `/api/data/pushups` response

```json
{
  "count": 7,
  "good_reps": 5,
  "bad_reps": 2,
  "stage": "READY",
  "feedback": "Rep 7! Perfect form",
  "feedback_color": "green",
  "form_score": 91,
  "angle_debug": {
    "elbow": 158,
    "back": 173,
    "flare": 41,
    "neck": 167
  },
  "ml_prediction": "good_form",
  "ml_confidence": 0.87,
  "final_feedback": "Rep 7! Perfect form"
}
```

---

## 🗄️ Database Schema

```
users
├── id              INTEGER  PRIMARY KEY
├── username        TEXT     UNIQUE NOT NULL
├── password_hash   TEXT     NOT NULL  ← bcrypt hash, never plain text
└── created_at      DATETIME

workout_sessions
├── id              INTEGER  PRIMARY KEY
├── user_id         INTEGER  FK → users.id  (cascade delete)
├── title           TEXT     e.g. "Session - Jan 15, 2025"
├── start_time      DATETIME
└── end_time        DATETIME

exercise_results
├── id              INTEGER  PRIMARY KEY
├── session_id      INTEGER  FK → workout_sessions.id  (cascade delete)
├── exercise_name   TEXT     e.g. "pushups"
├── duration_seconds INTEGER
├── total_reps      INTEGER
├── good_reps       INTEGER
├── bad_reps        INTEGER
├── avg_form_score  FLOAT
└── common_mistakes JSON     e.g. ["Tuck your elbows", "Go lower"]
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Pose AI** | MediaPipe BlazePose | Detects 33 body landmarks per frame using a pre-trained neural network |
| **Vision** | OpenCV (cv2) | Webcam capture, frame flipping, BGR→RGB, JPEG encoding |
| **Math** | NumPy | arctan2 angle calculation, coordinate array operations |
| **ML** | scikit-learn | RandomForestClassifier — ensemble of 100 decision trees |
| **Web Server** | Flask 3.x | HTTP server, routing, MJPEG streaming, Blueprint organization |
| **Auth** | Flask-JWT-Extended + bcrypt | JWT token creation/verification, password hashing |
| **Database** | SQLAlchemy + SQLite | ORM for 3-table schema, zero-config file-based storage |
| **Frontend** | React 18 + React Router 6 | SPA with client-side routing, hooks, context |
| **Charts** | Recharts | LineChart and PieChart for dashboard |
| **Voice** | Web Speech API | Browser-native text-to-speech, no external library |

---

## ⚙️ Configuration

### Backend thresholds (push-ups)

Adjust form strictness in `backend/analyzers/pushups.py`:

```python
THRESHOLDS = {
    "back_straight": 160,  "back_sag": 130,       # Back/hip posture (25 pts max)
    "flare_ideal":    55,  "flare_wide":  85,      # Elbow flare (20 pts max)
    "lockout_ideal": 150,  "lockout_bent": 130,    # Top extension (20 pts max)
    "depth_ideal":    90,  "depth_shallow": 120,   # Bottom depth (20 pts max)
    "neck_straight": 160,  "neck_craned": 140,     # Head alignment (15 pts max)
}
```

### EMA smoothing

Adjust jitter suppression vs. responsiveness in `backend/state/exercise_state.py`:

```python
"smoothing_alpha": 0.4,  # 0.0 = max smooth / slow, 1.0 = no smoothing / fast
```

### JWT secret

Change the JWT secret key in `backend/app.py` before deploying:

```python
app.config["JWT_SECRET_KEY"] = "your-strong-secret-key-here"
```

---

## ➕ Adding a New Exercise

1. **Add state entry** in `backend/state/exercise_state.py` — `exercise_states` dict + `_DEFAULTS` tuple
2. **Write analyzer** — create `backend/analyzers/your_exercise.py` implementing `analyze_your_exercise(landmarks, w, h, state)`
3. **Register analyzer** — add to `ANALYZERS` dict in `backend/analyzers/__init__.py`
4. **Add exercise card** — add object to `EXERCISES` array in `src/pages/HomePage.js`
5. **Add trainer metadata** — add entry to `EXERCISE_INFO` in `src/pages/TrainerPage.js` with name, icon, color, tips, keyAngles, setupInstructions

The video stream, polling loop, form score display, voice feedback, save flow, and history tracking all work automatically — they're driven by the exercise ID string.

---

## 📋 Requirements

### Python (`requirements.txt`)

```
flask
flask-cors
flask-jwt-extended
flask-sqlalchemy
opencv-python
mediapipe
numpy
bcrypt
scikit-learn
pandas
```

### Node.js (`package.json` key dependencies)

```json
{
  "react": "^18.0.0",
  "react-dom": "^18.0.0",
  "react-router-dom": "^6.0.0",
  "recharts": "^2.0.0",
  "proxy": "http://localhost:5000"
}
```

---

## 🧪 Known Limitations

- **Single camera stream** — Only one exercise can stream at a time (by design — threading lock prevents camera conflicts)
- **Side-on camera** — Most exercises require a side or diagonal view for accurate joint angle measurement. Front-facing can cause poor detection on squats/push-ups
- **Lighting sensitivity** — MediaPipe detection degrades significantly in low or backlit environments
- **ML models need data** — The bundled `.pkl` models were trained on limited data; accuracy improves as you generate more reps in your CSV files and retrain
- **Local only** — Designed as a desktop application; the MJPEG streaming approach is not optimal for multi-user deployment

---

## 🗺️ Roadmap

- [ ] Deadlift and plank support
- [ ] Multi-camera angle support
- [ ] Workout plan builder (sets × reps targets)
- [ ] Side-by-side form comparison (your rep vs. ideal form skeleton)
- [ ] Export workout history to CSV
- [ ] Progressive overload tracking

---

## 📄 License

This project is open source. Feel free to use, modify, and distribute.

---

<div align="center">

Built with &nbsp;**OpenCV** · **MediaPipe** · **Flask** · **React** · **scikit-learn**

**Star ⭐ the repo if FormFit helped your training!**

</div>
