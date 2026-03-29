import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config';
import './AuthPage.css';

export default function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, register, token } = useAuth();
  
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // If already logged in, instantly route back where they came from
  useEffect(() => {
    if (token) {
      if (location.state?.returnTo) {
         navigate(location.state.returnTo);
      } else {
         navigate('/');
      }
    }
  }, [token, navigate, location]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const action = isLogin ? login : register;
      const res = await action(username, password);

      if (!res.success) {
        setError(res.error || 'Authentication failed');
      } else {
        // Successful login/register will automatically trigger the useEffect above
        // However, if we came from TrainerPage and they clicked "Save & Exit",
        // we might have a pending save operation stored in localStorage.
        const pendingSave = localStorage.getItem('pending_save');
        if (pendingSave) {
           const payload = JSON.parse(pendingSave);
           localStorage.removeItem('pending_save');
           
           // Fire the save request to the protected endpoint instantly
           await fetch(`${API_BASE_URL}/api/history/save`, {
             method: 'POST',
             headers: { 
               'Content-Type': 'application/json',
               'Authorization': `Bearer ${res.token || localStorage.getItem('formfit_token')}` // use fresh token
             },
             body: JSON.stringify(payload)
           });
           
           // Send them to history directly so they see their saved result
           navigate('/history');
        }
      }
    } catch (err) {
      setError('A network error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <button className="auth-back" onClick={() => navigate('/')}>
        ← Back to Menu
      </button>

      <div className="auth-card">
        <h1 className="auth-title">{isLogin ? 'Welcome Back' : 'Create Account'}</h1>
        
        {error && <div className="auth-error">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <input 
            type="text" 
            placeholder="Username" 
            className="auth-input" 
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            autoComplete="username"
          />
          <input 
            type="password" 
            placeholder="Password" 
            className="auth-input" 
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoComplete={isLogin ? "current-password" : "new-password"}
          />
          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? 'Processing...' : (isLogin ? 'Login' : 'Sign Up')}
          </button>
        </form>

        <button 
          className="auth-toggle" 
          onClick={() => { setIsLogin(!isLogin); setError(''); }}
        >
          {isLogin ? "Don't have an account? Sign up" : "Already have an account? Login"}
        </button>
      </div>
    </div>
  );
}
