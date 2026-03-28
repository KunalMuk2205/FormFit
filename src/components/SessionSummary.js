import React, { useMemo } from 'react';
import './SessionSummary.css';

// Maps raw feedback strings to friendly display labels
const MISTAKE_LABELS = [
  { match: 'elbow',   label: 'Elbows too wide',         icon: '💪' },
  { match: 'lower',   label: 'Not going low enough',     icon: '📉' },
  { match: 'depth',   label: 'Insufficient depth',       icon: '📉' },
  { match: 'shallow', label: 'Not going low enough',     icon: '📉' },
  { match: 'back',    label: 'Back not straight',        icon: '📐' },
  { match: 'straight',label: 'Posture misaligned',       icon: '📐' },
  { match: 'knee',    label: 'Knees caving inward',      icon: '🦵' },
  { match: 'tuck',    label: 'Elbows flaring out',       icon: '💪' },
  { match: 'neck',    label: 'Head position off',        icon: '🔺' },
];

function friendlyMistake(raw) {
  const lower = raw.toLowerCase();
  const match = MISTAKE_LABELS.find(m => lower.includes(m.match));
  return match || { label: raw, icon: '⚠️' };
}

export default function SessionSummary({ 
  info, 
  elapsed, 
  data, 
  mistakesList, 
  onDiscard, 
  onSave, 
  isSaving 
}) {
  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  const analytics = useMemo(() => {
    if (!mistakesList || mistakesList.length === 0) {
      return {
        topMistakes: [],
        suggestion: "Flawless execution! You are ready to increase resistance or aim for higher volumes.",
      };
    }

    // Tally frequencies
    const freq = {};
    mistakesList.forEach(m => {
      freq[m] = (freq[m] || 0) + 1;
    });

    // Sort by frequency
    const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]);
    const topMistakes = sorted.slice(0, 2); // Pull Top 2 Most Frequent
    const primaryMistake = sorted[0][0].toLowerCase();

    // AI Suggestion Dictionary match
    let suggestion = "Keep practicing to refine your overall form consistency throughout the entire movement phase.";
    
    if (primaryMistake.includes('elbow')) {
      suggestion = "Elbow flare was detected frequently. Focus on keeping your elbows pinned tighter to your ribs to protect your rotator cuffs.";
    } else if (primaryMistake.includes('lower') || primaryMistake.includes('depth')) {
      suggestion = "You are regularly missing full depth. Drop the resistance slightly and focus on pausing for 1 full second at the very bottom of each rep.";
    } else if (primaryMistake.includes('straight') || primaryMistake.includes('back')) {
      suggestion = "Your spinal alignment is shifting. Engage your core tightly and treat your back like a rigid steel plank.";
    } else if (primaryMistake.includes('knee')) {
      suggestion = "Your knee tracking is inconsistent. Imagine pushing the floor apart with the sides of your feet to activate your glutes and stabilize your leg columns.";
    }

    return { topMistakes, suggestion };
  }, [mistakesList]);

  return (
    <div className="modal-overlay">
      <div className="summary-modal" style={{ '--modal-color': info.color }}>
        <div className="modal-body-scroll">
          <h2 className="modal-title">Session Complete</h2>
          
          <div className="modal-stats">
          <div className="m-stat">
            <span className="m-label">EXERCISE</span>
            <span className="m-val">{info.name}</span>
          </div>
          <div className="m-stat">
            <span className="m-label">TIME</span>
            <span className="m-val mono">{formatTime(elapsed)}</span>
          </div>
          <div className="m-stat">
            <span className="m-label">FINAL SCORE</span>
            <span className="m-val score">{data.form_score}/100</span>
          </div>
          <div className="m-stat full-width">
            <span className="m-label">TOTAL REPS: {data.count}</span>
            <div className="m-rep-bar">
              <div className="m-rep-good" style={{ width: `${data.count > 0 ? (data.good_reps / data.count) * 100 : 0}%` }}>{data.good_reps} Good</div>
              <div className="m-rep-bad" style={{ width: `${data.count > 0 ? (data.bad_reps / data.count) * 100 : 0}%` }}>{data.bad_reps} Flawed</div>
            </div>
          </div>
        </div>

        <div className="modal-analytics" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
          <div className="analytics-section">
            <span className="m-label">TOP MISTAKES DETECTED</span>
            {analytics.topMistakes.length > 0 ? (
              <ul className="mistakes-list">
                {analytics.topMistakes.map(([mistake, count], idx) => {
                  const { label, icon } = friendlyMistake(mistake);
                  const maxCount = analytics.topMistakes[0][1];
                  const pct = Math.round((count / maxCount) * 100);
                  return (
                    <li key={idx} className="mistake-row">
                      <span className="mistake-rank">#{idx + 1}</span>
                      <div className="mistake-body">
                        <div className="mistake-header">
                          <span className="mistake-icon">{icon}</span>
                          <span className="mistake-label">{label}</span>
                          <span className="mistake-count">{count}x</span>
                        </div>
                        <div className="mistake-bar-track">
                          <div className="mistake-bar-fill" style={{ width: `${pct}%`, opacity: idx === 0 ? 1 : 0.55 }} />
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="perfect-score">✨ No consistent mistakes detected.</p>
            )}
          </div>
          
          <div className="analytics-section ai-suggestion">
            <span className="m-label">💡 AI IMPROVEMENT SUGGESTION</span>
            <p className="suggestion-text">{analytics.suggestion}</p>
          </div>
        </div>
        </div>

        <div className="modal-actions">
          <button className="modal-btn ghost" onClick={onDiscard}>Discard Session</button>
          <button className="modal-btn solid" onClick={onSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save Workout'}
          </button>
        </div>
      </div>
    </div>
  );
}
