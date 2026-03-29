import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SessionSummary from '../components/SessionSummary';
import { API_BASE_URL } from '../config';
import './TrainerPage.css';

const EXERCISE_INFO = {
  pushups: {
    name: 'Push-Ups',
    icon: '💪',
    color: '#00ff87',
    tips: [
      'Keep your body in a straight line from head to heels',
      'Tuck elbows close to body — aim for 45° flare angle',
      'Lower until chest nearly touches the floor',
      'Breathe out on the way up',
    ],
    keyAngles: ['Elbow angle (target: <90° down, >150° up)', 'Back/hip angle (target: >160° for straight)', 'Elbow flare (target: <55°)'],
    setupInstructions: [
      'Face sideways or slightly diagonal to the camera',
      'Keep your full body in frame',
      'Make sure shoulders, elbows, hips, and ankles are visible'
    ],
  },
  squats: {
    name: 'Squats',
    icon: '🦵',
    color: '#00c2ff',
    tips: [
      'Keep feet shoulder-width apart, toes slightly out',
      'Push knees out in line with toes',
      'Drive hips back and down — sit into the squat',
      'Keep chest up and back neutral',
    ],
    keyAngles: ['Knee angle (target: <100° at bottom)', 'Hip angle (monitors depth)', 'Knee tracking (no caving)'],
    setupInstructions: [
      'Stand sideways to the camera',
      'Keep your full body in frame',
      'Make sure hips, knees, and ankles are clearly visible'
    ],
  },
  bicep_curls: {
    name: 'Bicep Curls',
    icon: '🏋️',
    color: '#ff6b35',
    tips: [
      'Keep elbows pinned to sides of your body',
      'Fully extend arms at the bottom of each rep',
      'Curl until forearms touch biceps at the top',
      'Control the lowering phase — don\'t drop',
    ],
    keyAngles: ['Left elbow angle (<50° up, >150° down)', 'Right elbow angle (symmetry check)', 'Elbow drift detection'],
    setupInstructions: [
      'Stand facing the camera or slightly diagonal',
      'Keep your upper body and arms fully visible',
      'Make sure shoulders, elbows, and wrists are in frame'
    ],
  },
  shoulder_press: {
    name: 'Shoulder Press',
    icon: '🔝',
    color: '#c77dff',
    tips: [
      'Start with elbows at 90° at shoulder height',
      'Press directly overhead, arms fully extended',
      'Keep core braced throughout the movement',
      'Lower slowly back to starting position',
    ],
    keyAngles: ['Left arm angle (>160° = full extension)', 'Right arm angle (symmetry check)', 'Shoulder range of motion'],
    setupInstructions: [
      'Stand facing the camera or slightly diagonal',
      'Keep your upper body and arms fully visible',
      'Make sure shoulders, elbows, and wrists are in frame'
    ],
  },
};

const FEEDBACK_COLORS = {
  green: '#00ff87',
  yellow: '#ffe566',
  cyan: '#00c2ff',
  orange: '#ff6b35',
  red: '#ff3b5c',
};

export default function TrainerPage() {
  const { exerciseId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const info = EXERCISE_INFO[exerciseId];

  const [data, setData] = useState({ 
    count: 0, 
    stage: '...', 
    feedback: 'Loading...', 
    feedback_color: 'yellow', 
    angle_debug: {},
    form_score: 100,
    good_reps: 0,
    bad_reps: 0
  });

  const visibleFeedback = data.final_feedback || data.feedback;

  const [isConnected, setIsConnected] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [sessionStart, setSessionStart] = useState(null);
  const [showSummary, setShowSummary] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  
  // Onboarding States
  const [hasStarted, setHasStarted] = useState(false);
  const [camError, setCamError] = useState(null);
  const [isCheckingCam, setIsCheckingCam] = useState(false);
  
  // Advanced Analytics State
  const [mistakesList, setMistakesList] = useState([]);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  
  const pollRef = useRef(null);
  const timerRef = useRef(null);
  const lastSpokenMsg = useRef('');
  const lastSpokenTime = useRef(0);

  useEffect(() => {
    if (!info || !hasStarted) return;
    setIsConnected(true);

    const abortController = new AbortController();
    let isSubscribed = true;

    // Adaptive Recursive Polling
    const poll = async () => {
      if (!isSubscribed) return;
      try {
        const res = await fetch(`${API_BASE_URL}/api/data/${exerciseId}`, {
          signal: abortController.signal
        });
        if (res.ok && isSubscribed) {
          const json = await res.json();
          setData(prev => JSON.stringify(prev) === JSON.stringify(json) ? prev : json);
          setIsConnected(true);
        }
      } catch (err) {
        if (err.name !== 'AbortError' && isSubscribed) {
          setIsConnected(false);
        }
      }

      if (isSubscribed) {
        pollRef.current = setTimeout(poll, 250);
      }
    };

    poll();

    // Elapsed timer
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - sessionStart) / 1000));
    }, 1000);

    return () => {
      isSubscribed = false;
      abortController.abort();
      clearTimeout(pollRef.current);
      clearInterval(timerRef.current);
      fetch(`${API_BASE_URL}/api/stop`, { method: 'POST' }).catch(() => {});
      
      // Prevent ghost speech if the user navigates away mid-sentence
      window.speechSynthesis.cancel();
    };
  }, [exerciseId, info, sessionStart, hasStarted]);

  // Voice Feedback Engine
  useEffect(() => {
    // 1. Guard against voice OFF or invalid strings
    if (!voiceEnabled || !visibleFeedback) return;

    // 2. Ignore generic transition statuses seamlessly
    const neutralMsgs = ['Loading...', '...', 'In position', 'Get ready', 'Ready'];
    if (neutralMsgs.includes(visibleFeedback)) return;

    const now = Date.now();
    const msgChanged = visibleFeedback !== lastSpokenMsg.current;
    const cooldownPassed = (now - lastSpokenTime.current) >= 2500;

    // 3. Stutter-proof execution layer: requires BOTH a changed message AND cleared 2.5s cooldown
    if (msgChanged && cooldownPassed) {
      
      // Log negative feedback into the arrays for End-Of-Session Analytics mapping!
      const isWarning = ['orange', 'red', 'yellow'].includes(data.feedback_color);
      if (isWarning && !neutralMsgs.includes(visibleFeedback)) {
        setMistakesList(prev => [...prev, visibleFeedback]);
      }

      window.speechSynthesis.cancel(); // Cleave any trailing echoes
      
      const utterance = new SpeechSynthesisUtterance(visibleFeedback);
      window.speechSynthesis.speak(utterance);
      
      lastSpokenMsg.current = visibleFeedback;
      lastSpokenTime.current = now;
    }
  }, [visibleFeedback, voiceEnabled, data.feedback_color]);

  const handleResetClick = () => {
    // Light UX constraint: Only ask if they actually have real progress
    if (data.count === 0 && elapsed < 10) {
      handleHardReset();
    } else {
      setShowResetConfirm(true);
    }
  };

  const handleHardReset = async () => {
    setShowResetConfirm(false);
    setShowSummary(false); // Clear if resetting from completed Modal
    await fetch(`${API_BASE_URL}/api/reset/${exerciseId}`, { method: 'POST' });
    setElapsed(0); 
    setSessionStart(Date.now());
    setMistakesList([]);
  };

  const handleSaveAndExit = async () => {
    const payload = {
      exercise_name: exerciseId,
      duration_seconds: elapsed,
      total_reps: data.count,
      good_reps: data.good_reps,
      bad_reps: data.bad_reps,
      avg_form_score: data.form_score,
      common_mistakes: []
    };

    if (!token) {
      // Unauthenticated users are paused, their data cached, and bounced to login
      localStorage.setItem('pending_save', JSON.stringify(payload));
      navigate('/auth', { state: { returnTo: '/history' } });
      return;
    }

    setIsSaving(true);
    try {
      await fetch(`${API_BASE_URL}/api/history/save`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify(payload)
      });
      await fetch(`${API_BASE_URL}/api/reset/${exerciseId}`, { method: 'POST' });
      navigate('/history');
    } catch (e) {
      console.error(e);
      setIsSaving(false);
    }
  };

  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  if (!info) {
    return (
      <div className="trainer-error">
        <p>Unknown exercise</p>
        <button onClick={() => navigate('/')}>← Back</button>
      </div>
    );
  }

  const fbColor = FEEDBACK_COLORS[data.feedback_color] || '#e8edf2';

  // --- HARDWARE VALIDATION ---
  const handleStartWorkout = async () => {
    setCamError(null);
    setIsCheckingCam(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      stream.getTracks().forEach(track => track.stop()); // Immediately shut off browser loop
      setSessionStart(Date.now()); // Mark start time accurately!
      setHasStarted(true);         // Boot backend hooks!
    } catch (err) {
      setCamError('Camera permission denied. Please click the padlock icon in your URL bar and allow Camera access.');
    } finally {
      setIsCheckingCam(false);
    }
  };

  // --- PRE-WORKOUT ONBOARDING SCREEN ---
  if (!hasStarted) {
    return (
      <div className="trainer" style={{ '--ex-color': info.color }}>
        <nav className="trainer-nav">
          <button className="back-btn" onClick={() => navigate('/')}>← Back</button>
          <div className="trainer-nav-title">
            <span>{info.icon}</span>
            <span>{info.name} Setup</span>
          </div>
          <div className="connection-indicator disconnected">
            <span className="conn-dot" /> Waiting to start
          </div>
        </nav>

        <div className="onboarding-layout">
          <div className="onboarding-card" style={{ borderColor: info.color }}>
            <h2 className="oboard-title">Get Ready for {info.name}</h2>
            <p className="oboard-subtitle">Please follow these framing instructions so the AI can track your skeleton accurately:</p>
            
            <ul className="oboard-list">
              {info.setupInstructions.map((instruction, idx) => (
                <li key={idx}>
                  <div className="check-icon" style={{ backgroundColor: info.color }}>✔</div>
                  <span>{instruction}</span>
                </li>
              ))}
              <li>
                <div className="check-icon" style={{ backgroundColor: info.color }}>✔</div>
                <span>Ensure good ambient lighting without harsh backlighting</span>
              </li>
            </ul>

            {camError && (
              <div className="cam-error-box">
                <strong>⚠️ Access Denied</strong>
                <p>{camError}</p>
              </div>
            )}

            <button 
              className="oboard-start-btn" 
              onClick={handleStartWorkout}
              disabled={isCheckingCam}
              style={{ backgroundColor: info.color }}
            >
              {isCheckingCam ? 'CHECKING HARDWARE...' : 'START WORKOUT'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // --- MAIN LIVE UI RENDERING ---
  return (
    <div className="trainer" style={{ '--ex-color': info.color }}>
      {/* Nav bar */}
      <nav className="trainer-nav">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← Back
        </button>
        <div className="trainer-nav-title">
          <span>{info.icon}</span>
          <span>{info.name}</span>
        </div>
        <div className={`connection-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
          <span className="conn-dot" />
          {isConnected ? 'Live' : 'Connecting...'}
        </div>
      </nav>

      <div className="trainer-layout">
        {/* Camera feed */}
        <div className="camera-panel">
          <div className="camera-frame">
            <img
              src={`${API_BASE_URL}/api/video/${exerciseId}`}
              alt="Live camera feed"
              className="camera-feed"
              onError={() => setIsConnected(false)}
            />
            {/* Stage badge overlay */}
            <div className="stage-badge">{data.stage}</div>
          </div>

          {/* Feedback bar */}
          <div className="feedback-bar" style={{ '--fb-color': fbColor, borderColor: fbColor }}>
            <span className="feedback-indicator" style={{ background: fbColor }} />
            <span className="feedback-text" style={{ color: fbColor }}>{visibleFeedback}</span>
          </div>

          {/* ML Explainability Badge — only shown after first rep when ML data is available */}
          {data.ml_prediction && (
            <div className="ml-badge-row">
              <span className={`ml-badge ${data.ml_prediction === 'good_form' ? 'ml-good' : 'ml-bad'}`}>
                {data.ml_prediction === 'good_form' ? '✅' : '⚠️'} ML: {data.ml_prediction.replace('_', ' ')}
              </span>
              {data.ml_confidence != null && (
                <span className="ml-conf-wrapper">
                  <span className="ml-conf-label">{(data.ml_confidence * 100).toFixed(0)}%</span>
                  <span className="ml-conf-bar-track">
                    <span
                      className={`ml-conf-bar-fill ${data.ml_prediction === 'good_form' ? 'ml-good' : 'ml-bad'}`}
                      style={{ width: `${data.ml_confidence * 100}%` }}
                    />
                  </span>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Stats panel */}
        <aside className="stats-panel">
          
          <div className="voice-control">
            <button 
              className={`voice-toggle ${voiceEnabled ? 'on' : 'off'}`}
              onClick={() => {
                setVoiceEnabled(!voiceEnabled);
                if (voiceEnabled) window.speechSynthesis.cancel(); // Stop talking instantly on mute
              }}
            >
              {voiceEnabled ? '🔊 Voice ON' : '🔇 Voice OFF'}
            </button>
          </div>

          {/* Rep counter */}
          <div className="stat-card rep-card">
            <div className="stat-label-small">TOTAL REPS</div>
            <div className="rep-number">{data.count}</div>
            <div className="rep-badges">
              <div className="rep-badge good-reps">
                <span className="badge-dot" /> {data.good_reps} Good
              </div>
              <div className="rep-badge bad-reps">
                <span className="badge-dot" /> {data.bad_reps} form issue
              </div>
            </div>
          </div>

          {/* Form Score Ring */}
          {data.form_score !== undefined && (() => {
            const score = Math.round(data.form_score);
            const ringColor = score >= 85 ? FEEDBACK_COLORS.green
                           : score >= 70 ? FEEDBACK_COLORS.yellow
                           : FEEDBACK_COLORS.orange;
            const label    = score >= 85 ? 'Excellent' : score >= 70 ? 'Good' : 'Needs Work';
            const R        = 44;
            const CIRC     = 2 * Math.PI * R;  // ≈ 276.5
            const dash     = CIRC * (score / 100);
            const gap      = CIRC - dash;
            return (
              <div className="stat-card score-ring-card">
                <div className="stat-label-small">LIVE FORM SCORE</div>
                <div className="score-ring-wrapper">
                  <svg className="score-ring-svg" viewBox="0 0 100 100">
                    {/* Track */}
                    <circle cx="50" cy="50" r={R} fill="none"
                      stroke="rgba(255,255,255,0.07)" strokeWidth="8" />
                    {/* Progress arc */}
                    <circle cx="50" cy="50" r={R} fill="none"
                      stroke={ringColor}
                      strokeWidth="8"
                      strokeLinecap="round"
                      strokeDasharray={`${dash} ${gap}`}
                      transform="rotate(-90 50 50)"
                      style={{ filter: `drop-shadow(0 0 6px ${ringColor})`, transition: 'stroke-dasharray 0.4s ease' }}
                    />
                  </svg>
                  {/* Centre label */}
                  <div className="score-ring-center">
                    <span className="score-ring-number" style={{ color: ringColor }}>{score}</span>
                    <span className="score-ring-unit">/ 100</span>
                  </div>
                </div>
                <div className="score-ring-label" style={{ color: ringColor }}>{label}</div>
              </div>
            );
          })()}

          {/* Session stats */}
          <div className="stat-card session-card">
            <div className="session-row">
              <div>
                <div className="stat-label-small">SESSION TIME</div>
                <div className="session-value mono">{formatTime(elapsed)}</div>
              </div>
              <div>
                <div className="stat-label-small">STAGE</div>
                <div className="session-value">{data.stage}</div>
              </div>
            </div>
          </div>

          {/* Angle debug */}
          {Object.keys(data.angle_debug).length > 0 && (
            <div className="stat-card angles-card">
              <div className="stat-label-small">LIVE ANGLES</div>
              <div className="angles-list">
                {Object.entries(data.angle_debug).map(([k, v]) => (
                  <div key={k} className="angle-row">
                    <span className="angle-name">{k.replace(/_/g, ' ')}</span>
                    <span className="angle-val mono">{v}°</span>
                    <div className="angle-bar-track">
                      <div className="angle-bar-fill" style={{ width: `${Math.min(v / 180 * 100, 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Key angles info */}
          <div className="stat-card info-card">
            <div className="stat-label-small">WHAT'S TRACKED</div>
            <ul className="info-list">
              {info.keyAngles.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>

          {/* Form tips */}
          <div className="stat-card tips-card">
            <div className="stat-label-small">FORM TIPS</div>
            <ul className="tips-list">
              {info.tips.map((t, i) => (
                <li key={i}><span className="tip-dot" />  {t}</li>
              ))}
            </ul>
          </div>

          {/* Actions */}
          <div className="action-buttons">
            <button className="reset-btn" onClick={handleResetClick}>
              ↺ Reset Session
            </button>
            <button className="save-btn" onClick={() => setShowSummary(true)}>
              ✔ Complete Session
            </button>
          </div>
        </aside>
      </div>

      {/* Analytics Modal Overlays */}
      {showSummary && (
        <SessionSummary 
          info={info}
          elapsed={elapsed}
          data={data}
          mistakesList={mistakesList}
          onDiscard={handleHardReset}
          onSave={handleSaveAndExit}
          isSaving={isSaving}
        />
      )}

      {/* Light Reset Confirmation Overlay */}
      {showResetConfirm && (
        <div className="modal-overlay">
          <div className="reset-confirm-card">
            <h3>Reset Workout?</h3>
            <p>You have recorded <strong>{data.count} reps</strong> in {formatTime(elapsed)}. Are you absolutely sure you want to discard this progress?</p>
            <div className="modal-actions">
              <button className="modal-btn ghost" onClick={() => setShowResetConfirm(false)}>Continue Workout</button>
              <button className="modal-btn solid" onClick={handleHardReset} style={{ background: '#ff3b5c', color: '#fff', border: 'none' }}>Discard Session</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
