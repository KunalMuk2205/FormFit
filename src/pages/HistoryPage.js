import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config';
import './HistoryPage.css';

const EXERCISE_COLORS = {
  pushups: '#00ff87',
  squats: '#00c2ff',
  bicep_curls: '#ff6b35',
  shoulder_press: '#c77dff'
};

const EXERCISE_NAMES = {
  pushups: 'Push-Ups',
  squats: 'Squats',
  bicep_curls: 'Bicep Curls',
  shoulder_press: 'Shoulder Press'
};

export default function HistoryPage() {
  const navigate = useNavigate();
  const { token, logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      navigate('/auth');
      return;
    }

    async function fetchHistory() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/history/`, {
          headers: { 'Authorization': `Bearer ${token}` },
          cache: 'no-store'
        });
        if (res.ok) {
          const data = await res.json();
          setSessions(data);
        } else if (res.status === 401) {
          logout();
          navigate('/auth');
        }
      } catch (e) {
        console.error("Failed to fetch history", e);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [token, navigate, logout]);

  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  return (
    <div className="history-page">
      <header className="history-header">
        <h1 className="history-title">Workout History</h1>
        <button className="history-back" onClick={() => navigate('/')}>
          ← Back to Menu
        </button>
      </header>

      <div className="history-content">
        {loading ? (
          <div className="empty-state">Loading your history...</div>
        ) : sessions.length === 0 ? (
          <div className="empty-state">
            No workouts saved yet. Hit the gym and complete a session!
          </div>
        ) : (
          sessions.map(session => {
            // Since our current flow creates one ExerciseResult per WorkoutSession,
            // we'll pull the first result to define the color and theme.
            const mainEx = session.exercises[0];
            const color = mainEx ? (EXERCISE_COLORS[mainEx.exercise_name] || '#00ff87') : '#00ff87';

            return (
              <div 
                key={session.id} 
                className="session-block" 
                style={{ '--ex-color': color }}
              >
                <div className="session-header">
                  <h2 className="session-title">{session.title}</h2>
                  <span className="session-date">
                    {new Date(session.start_time).toLocaleString(undefined, {
                      weekday: 'short', month: 'short', day: 'numeric',
                      hour: 'numeric', minute: '2-digit'
                    })}
                  </span>
                </div>

                {session.exercises.map(ex => (
                  <div key={ex.id} className="ex-result">
                    <div className="ex-stat">
                      <span className="ex-stat-label">EXERCISE</span>
                      <span className="ex-stat-val">
                        {EXERCISE_NAMES[ex.exercise_name] || ex.exercise_name}
                      </span>
                    </div>

                    <div className="ex-stat">
                      <span className="ex-stat-label">DURATION</span>
                      <span className="ex-stat-val">{formatTime(ex.duration_seconds)}</span>
                    </div>

                    <div className="ex-stat">
                      <span className="ex-stat-label">FORM SCORE</span>
                      <span className="ex-stat-val score-val">{ex.avg_form_score}/100</span>
                    </div>

                    <div className="ex-stat" style={{ gridColumn: '1 / -1' }}>
                      <span className="ex-stat-label">REP COMPLETION</span>
                      <div className="rep-breakdown">
                        <span className="ex-stat-val">{ex.total_reps} TOTAL</span>
                        <span className="good-pill">{ex.good_reps} GOOD</span>
                        {ex.bad_reps > 0 && <span className="bad-pill">{ex.bad_reps} FLAWED</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
