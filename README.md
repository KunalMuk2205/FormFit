# ⚡ FormFit — AI Exercise Form Trainer

Real-time posture detection for Push-ups, Squats, Bicep Curls, and Shoulder Press using MediaPipe + OpenCV with a React frontend.

---

## 🏗️ Architecture

```
formfit/
├── backend/          # Flask + OpenCV + MediaPipe
│   ├── app.py        # Main server, pose analysis, MJPEG stream
│   └── requirements.txt
└── frontend/         # React app
    ├── src/
    │   ├── pages/
    │   │   ├── HomePage.js      # Exercise selection
    │   │   └── TrainerPage.js   # Live trainer view
    │   └── App.js
    └── package.json
```

---

## 🚀 Setup & Run

### 1. Backend (Python)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```
Flask will run at `http://localhost:5000`

---

### 2. Frontend (React)

Open a **new terminal**:

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm start
```
React will open at `http://localhost:3000`

---

## 🎯 Exercises & What's Tracked

| Exercise       | Key Angles                                      | Form Checks                     |
|----------------|--------------------------------------------------|----------------------------------|
| Push-Ups       | Elbow angle, back/hip angle, elbow flare        | Elbow flare > 55° → warning      |
| Squats         | Knee angle, hip angle                           | Knee caving detection            |
| Bicep Curls    | Left & right elbow angles                       | Elbow drift from body            |
| Shoulder Press | Left & right arm angles                         | Full extension overhead          |

---

## 🔌 API Endpoints

| Endpoint                     | Method | Description                       |
|------------------------------|--------|-----------------------------------|
| `/api/video/<exercise_id>`   | GET    | MJPEG stream with pose overlay    |
| `/api/data/<exercise_id>`    | GET    | JSON: reps, stage, feedback       |
| `/api/reset/<exercise_id>`   | POST   | Reset session counters            |
| `/api/health`                | GET    | Health check                      |

**Exercise IDs:** `pushups`, `squats`, `bicep_curls`, `shoulder_press`

---

## 🛠️ Technologies

- **Backend:** Python, Flask, OpenCV, MediaPipe, NumPy
- **Frontend:** React, React Router

---

## 💡 Extending with New Exercises

1. Add a new state entry in `exercise_states` dict in `app.py`
2. Write an `analyze_<name>(landmarks, w, h, state)` function
3. Register it in the `ANALYZERS` dict
4. Add the exercise card in `HomePage.js` and metadata in `TrainerPage.js`
