const express = require('express');
const { v4: uuidv4 } = require('uuid');
const { getRedisClient } = require('../config/redis');

const router = express.Router();

// Simple user login/registration (no passwords for demo)
router.post('/login', async (req, res) => {
  try {
    const { username } = req.body;

    if (!username || username.trim().length === 0) {
      return res.status(400).json({ error: 'Username is required' });
    }

    const trimmedUsername = username.trim();
    
    if (trimmedUsername.length < 2 || trimmedUsername.length > 20) {
      return res.status(400).json({ error: 'Username must be 2-20 characters' });
    }

    const redisClient = getRedisClient();
    const userId = uuidv4();
    const sessionId = uuidv4();

    // Store user session in Redis (expires in 24 hours)
    const userSession = {
      userId,
      username: trimmedUsername,
      loginTime: new Date().toISOString(),
      isActive: true
    };

    await redisClient.setEx(`session:${sessionId}`, 86400, JSON.stringify(userSession));
    await redisClient.setEx(`user:${userId}`, 86400, JSON.stringify(userSession));

    console.log(`👤 User logged in: ${trimmedUsername} (${userId})`);

    res.json({
      success: true,
      user: {
        userId,
        username: trimmedUsername
      },
      sessionId,
      message: 'Login successful'
    });

  } catch (error) {
    console.error('❌ Login error:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

// Verify session
router.get('/verify/:sessionId', async (req, res) => {
  try {
    const { sessionId } = req.params;
    const redisClient = getRedisClient();

    const sessionData = await redisClient.get(`session:${sessionId}`);
    
    if (!sessionData) {
      return res.status(401).json({ error: 'Invalid or expired session' });
    }

    const user = JSON.parse(sessionData);

    res.json({
      success: true,
      user: {
        userId: user.userId,
        username: user.username
      }
    });

  } catch (error) {
    console.error('❌ Session verification error:', error);
    res.status(500).json({ error: 'Session verification failed' });
  }
});

// Logout
router.post('/logout/:sessionId', async (req, res) => {
  try {
    const { sessionId } = req.params;
    const redisClient = getRedisClient();

    // Get session to log username
    const sessionData = await redisClient.get(`session:${sessionId}`);
    if (sessionData) {
      const user = JSON.parse(sessionData);
      console.log(`👋 User logged out: ${user.username}`);
    }

    // Delete session
    await redisClient.del(`session:${sessionId}`);

    res.json({ success: true, message: 'Logged out successfully' });

  } catch (error) {
    console.error('❌ Logout error:', error);
    res.status(500).json({ error: 'Logout failed' });
  }
});

module.exports = router;