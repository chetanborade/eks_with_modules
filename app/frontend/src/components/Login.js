import React, { useState } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim()) return;

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE}/api/auth/login`, {
        username: username.trim()
      });

      onLogin({
        userId: response.data.user.userId,
        username: response.data.user.username,
        sessionId: response.data.sessionId
      });
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <form onSubmit={handleSubmit} className="login-form">
        <input
          type="text"
          placeholder="Enter your username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={loading}
          maxLength={20}
        />
        <button type="submit" disabled={loading || !username.trim()}>
          {loading ? 'Logging in...' : 'Start Playing'}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}

export default Login;