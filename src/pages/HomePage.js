import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './HomePage.css';

const EXERCISES = [
  {
    id: 'pushups',
    name: 'Push-Ups',
    muscles: 'Chest · Triceps · Shoulders',
    difficulty: 'Beginner',
    difficultyLevel: 1,
    description: 'Tracks elbow angle & back straightness. Detects elbow flare in real time.',
    icon: '💪',
    color: '#00ff87',
    grad: 'linear-gradient(135deg, #00ff8722 0%, #00ff8705 100%)',
    border: '#00ff87',
  },
  {
    id: 'squats',
    name: 'Squats',
    muscles: 'Quads · Glutes · Hamstrings',
    difficulty: 'Beginner',
    difficultyLevel: 1,
    description: 'Monitors knee angle & depth. Alerts for knee caving and incomplete reps.',
    icon: '🦵',
    color: '#00c2ff',
    grad: 'linear-gradient(135deg, #00c2ff22 0%, #00c2ff05 100%)',
    border: '#00c2ff',
  },
  {
    id: 'bicep_curls',
    name: 'Bicep Curls',
    muscles: 'Biceps · Forearms',
    difficulty: 'Intermediate',
    difficultyLevel: 2,
    description: 'Checks full range of motion. Warns when elbows drift away from body.',
    icon: '🏋️',
    color: '#ff6b35',
    grad: 'linear-gradient(135deg, #ff6b3522 0%, #ff6b3505 100%)',
    border: '#ff6b35',
  },
  {
    id: 'shoulder_press',
    name: 'Shoulder Press',
    muscles: 'Deltoids · Triceps · Traps',
    difficulty: 'Intermediate',
    difficultyLevel: 2,
    description: 'Tracks full arm extension overhead and controlled lowering to shoulder level.',
    icon: '🔝',
    color: '#c77dff',
    grad: 'linear-gradient(135deg, #c77dff22 0%, #c77dff05 100%)',
    border: '#c77dff',
  },
];

function DifficultyDots({ level }) {
  return (
    <div className="difficulty-dots">
      {[1, 2, 3].map(i => (
        <span key={i} className={`dot ${i <= level ? 'active' : ''}`} />
      ))}
    </div>
  );
}

export default function HomePage() {
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const { token, user, logout } = useAuth();

  // Animated particle background
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animFrame;
    const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; };
    resize();
    window.addEventListener('resize', resize);

    const particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.5 + 0.3,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      alpha: Math.random() * 0.5 + 0.1,
    }));

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0,255,135,${p.alpha})`;
        ctx.fill();
      });
      animFrame = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(animFrame); window.removeEventListener('resize', resize); };
  }, []);

  return (
    <div className="home">
      <canvas className="bg-canvas" ref={canvasRef} />

      {/* Header */}
      <header className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', maxWidth: '1200px', margin: '0 auto', padding: '32px' }}>
        <div>
          <div className="logo">
            <span className="logo-icon">⚡</span>
            <span className="logo-text">FORMFIT</span>
          </div>
          <p className="logo-tagline">AI-Powered Exercise Form Trainer</p>
        </div>
        
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          {token && user ? (
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '0.9rem' }}>
              <span>Hi, {user.username}</span>
              <button 
                onClick={logout} 
                style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-dim)', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer' }}
              >Logout</button>
            </div>
          ) : (
            <button 
              onClick={() => navigate('/auth')}
              style={{ background: 'var(--ex-color, #00ff87)', border: 'none', color: '#000', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontWeight: 'bold' }}
            >Sign In</button>
          )}

          <button 
            onClick={() => token ? navigate('/history') : navigate('/auth', { state: { returnTo: '/history' } })}
            style={{
              background: 'var(--bg-3)', border: '1px solid var(--border-bright)', color: 'var(--text)',
              padding: '12px 24px', borderRadius: '10px', fontFamily: 'var(--font-mono)', fontSize: '0.9rem',
              cursor: 'pointer', letterSpacing: '1px', transition: 'all 0.2s', display: 'flex', gap: '8px', alignItems: 'center'
            }}
            onMouseOver={e => { e.currentTarget.style.borderColor = 'var(--ex-color, #00ff87)'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)' }}
            onMouseOut={e => { e.currentTarget.style.borderColor = 'var(--border-bright)'; e.currentTarget.style.background = 'var(--bg-3)' }}
          >
            <span>📅</span> View History
          </button>
          
          <button 
            onClick={() => token ? navigate('/dashboard') : navigate('/auth', { state: { returnTo: '/dashboard' } })}
            style={{
              background: 'rgba(0, 194, 255, 0.1)', border: '1px solid rgba(0, 194, 255, 0.5)', color: '#00c2ff',
              padding: '12px 24px', borderRadius: '10px', fontFamily: 'var(--font-mono)', fontSize: '0.9rem',
              cursor: 'pointer', letterSpacing: '1px', transition: 'all 0.2s', display: 'flex', gap: '8px', alignItems: 'center'
            }}
            onMouseOver={e => { e.currentTarget.style.background = 'rgba(0, 194, 255, 0.2)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
            onMouseOut={e => { e.currentTarget.style.background = 'rgba(0, 194, 255, 0.1)'; e.currentTarget.style.transform = 'translateY(0)' }}
          >
            <span>📈</span> Dashboard
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="hero">
        <div className="hero-badge">
          <span className="badge-dot" />
          REAL-TIME POSE DETECTION
        </div>
        <h1 className="hero-title">
          PERFECT<br />
          <span className="hero-accent">FORM.</span><br />
          EVERY REP.
        </h1>
        <p className="hero-sub">
          MediaPipe body tracking detects joint angles, counts reps, and corrects your posture before injury happens.
        </p>
        <div className="hero-stats">
          <div className="stat"><span className="stat-num">33</span><span className="stat-label">Body landmarks</span></div>
          <div className="stat-sep" />
          <div className="stat"><span className="stat-num">4</span><span className="stat-label">Exercises</span></div>
          <div className="stat-sep" />
          <div className="stat"><span className="stat-num">60</span><span className="stat-label">FPS tracking</span></div>
        </div>
      </section>

      {/* Exercise cards */}
      <section className="exercises-section">
        <div className="section-label">— SELECT EXERCISE —</div>
        <div className="cards-grid">
          {EXERCISES.map((ex, i) => (
            <div
              key={ex.id}
              className="card"
              style={{
                '--card-color': ex.color,
                '--card-grad': ex.grad,
                animationDelay: `${i * 0.1}s`,
              }}
              onClick={() => navigate(`/trainer/${ex.id}`)}
            >
              <div className="card-top">
                <span className="card-icon">{ex.icon}</span>
                <div className="card-meta">
                  <span className="card-difficulty">{ex.difficulty}</span>
                  <DifficultyDots level={ex.difficultyLevel} />
                </div>
              </div>
              <h2 className="card-name">{ex.name}</h2>
              <p className="card-muscles">{ex.muscles}</p>
              <p className="card-desc">{ex.description}</p>
              <div className="card-footer">
                <span className="card-cta">Start Training →</span>
                <div className="card-glow" />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="how-section">
        <div className="section-label">— HOW IT WORKS —</div>
        <div className="steps">
          {[
            { n: '01', title: 'Camera On', desc: 'Your webcam feed is processed locally. Nothing is stored.' },
            { n: '02', title: 'Pose Detected', desc: 'MediaPipe maps 33 body landmarks every frame.' },
            { n: '03', title: 'Angles Calculated', desc: 'Joint angles are measured to evaluate your form.' },
            { n: '04', title: 'Live Feedback', desc: 'Rep counts and form cues appear on screen in real time.' },
          ].map(s => (
            <div className="step" key={s.n}>
              <span className="step-num">{s.n}</span>
              <h3 className="step-title">{s.title}</h3>
              <p className="step-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="footer">
        <p>Built with OpenCV · MediaPipe · Flask · React</p>
      </footer>
    </div>
  );
}
