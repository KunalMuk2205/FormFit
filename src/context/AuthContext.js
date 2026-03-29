import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('formfit_token'));
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('formfit_user')));

  useEffect(() => {
    if (token) {
      localStorage.setItem('formfit_token', token);
    } else {
      localStorage.removeItem('formfit_token');
    }
    
    if (user) {
      localStorage.setItem('formfit_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('formfit_user');
    }
  }, [token, user]);

  const login = async (username, password) => {
    const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    const data = await res.json();
    if (res.ok) {
      setToken(data.access_token);
      setUser(data.user);
      return { success: true, token: data.access_token };
    }
    return { success: false, error: data.error };
  };

  const register = async (username, password) => {
    const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    const data = await res.json();
    if (res.ok) {
      // Auto-login after successful registration
      return await login(username, password);
    }
    return { success: false, error: data.error };
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
