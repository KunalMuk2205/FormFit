import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { API_BASE_URL } from '../config';
import './DashboardPage.css';

const EXERCISE_COLORS = {
  pushups: '#00ff87',
  squats: '#00c2ff',
  bicep_curls: '#ff6b35',
  shoulder_press: '#c77dff'
};

const EXERCISE_NAMES = {
  pushups: 'Push-Ups',
  squats: 'Squats',
  bicep_curls: 'Curls',
  shoulder_press: 'Press'
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const { token, logout } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    if (!token) {
      navigate('/auth');
      return;
    }

    async function fetchDashboardData() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/history/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const sessions = await res.json();
          processData(sessions);
        } else if (res.status === 401) {
          logout();
          navigate('/auth');
        }
      } catch (e) {
        console.error("Dashboard fetch error", e);
      } finally {
        setLoading(false);
      }
    }
    fetchDashboardData();
  }, [token, navigate, logout]);

  // Client-Side Data Aggregation Engine
  const processData = (sessions) => {
    if (!sessions || sessions.length === 0) {
      setMetrics(null);
      return;
    }

    let totalReps = 0;
    let totalGoodReps = 0;
    let sumScore = 0;
    let validExCount = 0;
    let bestSessionScore = 0;

    const repsDict = {};
    const dateMap = {};
    const recentList = [];

    // Reverse sessions so oldest is processed first for chronological charts
    const sortedSessions = [...sessions].reverse();

    sortedSessions.forEach(session => {
      const dateKey = new Date(session.start_time).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      if (!dateMap[dateKey]) dateMap[dateKey] = { date: dateKey, reps: 0, scoreSum: 0, scoreCount: 0 };

      session.exercises.forEach(ex => {
        // Grand Totals
        totalReps += ex.total_reps;
        totalGoodReps += ex.good_reps;
        if (ex.avg_form_score > 0) {
          sumScore += ex.avg_form_score;
          validExCount++;
        }
        if (ex.avg_form_score > bestSessionScore) bestSessionScore = ex.avg_form_score;

        // Pie Chart Aggregation
        repsDict[ex.exercise_name] = (repsDict[ex.exercise_name] || 0) + ex.total_reps;

        // Line Chart Aggregation
        dateMap[dateKey].reps += ex.total_reps;
        if (ex.avg_form_score > 0) {
          dateMap[dateKey].scoreSum += ex.avg_form_score;
          dateMap[dateKey].scoreCount++;
        }

        // Recent Workouts (Take the last 5 later since we reversed)
        recentList.push({
          date: new Date(ex.completed_at).toLocaleDateString(),
          name: EXERCISE_NAMES[ex.exercise_name] || ex.exercise_name,
          reps: ex.total_reps,
          score: ex.avg_form_score
        });
      });
    });

    // Format Pie Data
    const pieData = Object.keys(repsDict).map(key => ({
      name: EXERCISE_NAMES[key] || key,
      value: repsDict[key],
      fill: EXERCISE_COLORS[key] || '#888'
    }));

    // Format Line Data
    const lineData = Object.values(dateMap).map(d => ({
      date: d.date,
      reps: d.reps,
      avgScore: d.scoreCount > 0 ? Math.round(d.scoreSum / d.scoreCount) : 0
    }));

    // Reverse recent back and slice top 5
    const topRecent = recentList.reverse().slice(0, 5);

    setMetrics({
      totalSessions: sessions.length,
      totalReps,
      totalGoodReps,
      avgFormScore: validExCount > 0 ? Math.round(sumScore / validExCount) : 0,
      bestSessionScore: Math.round(bestSessionScore),
      pieData,
      lineData,
      recentWorkouts: topRecent
    });
  };

  if (loading) return <div className="dash-loading">Compiling metrics...</div>;

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <h1 className="dashboard-title">Performance Dashboard</h1>
        <button className="dashboard-back" onClick={() => navigate('/')}>
          ← Back
        </button>
      </header>

      {!metrics ? (
        <div className="dash-empty">
          You haven't completed any workouts yet! Complete a session to unlock analytics.
        </div>
      ) : (
        <div className="dashboard-content">

          {/* KPI ROW */}
          <div className="kpi-row">
            <div className="kpi-card" style={{ '--kpi-color': '#00ff87' }}>
              <span className="kpi-label">Workouts</span>
              <span className="kpi-value">{metrics.totalSessions}</span>
              <span className="kpi-subtext">Total recorded sessions</span>
            </div>
            <div className="kpi-card" style={{ '--kpi-color': '#00c2ff' }}>
              <span className="kpi-label">Total Volume</span>
              <span className="kpi-value">{metrics.totalReps}</span>
              <span className="kpi-subtext">{metrics.totalGoodReps} perfect reps</span>
            </div>
            <div className="kpi-card" style={{ '--kpi-color': metrics.avgFormScore > 85 ? '#00ff87' : '#ff6b35' }}>
              <span className="kpi-label">Avg Form Score</span>
              <span className="kpi-value">{metrics.avgFormScore}</span>
              <span className="kpi-subtext">out of 100</span>
            </div>
            <div className="kpi-card" style={{ '--kpi-color': '#c77dff' }}>
              <span className="kpi-label">Peak Performance</span>
              <span className="kpi-value">{metrics.bestSessionScore}</span>
              <span className="kpi-subtext">Highest form rating</span>
            </div>
          </div>

          {/* CHARTS ROW */}
          <div className="charts-row">
            <div className="chart-card">
              <h3 className="chart-title">Weekly Volume & Form</h3>
              <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                  <LineChart data={metrics.lineData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <XAxis dataKey="date" stroke="#666" tick={{ fill: '#aaa' }} />
                    <YAxis yAxisId="left" stroke="#00c2ff" tick={{ fill: '#00c2ff' }} />
                    <YAxis yAxisId="right" orientation="right" stroke="#00ff87" tick={{ fill: '#00ff87' }} domain={[0, 100]} />
                    <Tooltip contentStyle={{ backgroundColor: '#111', borderColor: '#333', color: '#fff' }} />
                    <Legend />
                    <Line yAxisId="left" type="monotone" dataKey="reps" stroke="#00c2ff" strokeWidth={3} dot={{ r: 4 }} name="Total Reps" />
                    <Line yAxisId="right" type="monotone" dataKey="avgScore" stroke="#00ff87" strokeWidth={3} dot={{ r: 4 }} name="Avg Form Score" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="chart-card">
              <h3 className="chart-title">Exercise Split</h3>
              <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={metrics.pieData} innerRadius={60} outerRadius={100} paddingAngle={5} dataKey="value">
                      {metrics.pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} stroke="rgba(0,0,0,0)" />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#111', borderColor: '#333', color: '#fff' }} />
                    <Legend verticalAlign="bottom" height={36} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* RECENT WORKOUTS ROW */}
          <div className="table-card">
            <h3 className="chart-title">Recent Workouts</h3>
            <table className="recent-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Exercise</th>
                  <th>Reps</th>
                  <th>Form Score</th>
                </tr>
              </thead>
              <tbody>
                {metrics.recentWorkouts.map((wk, i) => (
                  <tr key={i}>
                    <td>{wk.date}</td>
                    <td style={{ color: EXERCISE_COLORS[wk.name.toLowerCase().replace('-', '')] || '#fff' }}>
                      {wk.name}
                    </td>
                    <td>{wk.reps} reps</td>
                    <td><span style={{ color: wk.score > 85 ? '#00ff87' : '#ff6b35' }}>{Math.round(wk.score)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </div>
      )}
    </div>
  );
}
