const express = require('express');
const axios = require('axios');
const { getRedisClient } = require('../config/redis');

const router = express.Router();

// Game engine service URL
const GAME_ENGINE_URL = process.env.GAME_ENGINE_URL || 'http://localhost:8000';

// Middleware to verify session
const verifySession = async (req, res, next) => {
  try {
    const sessionId = req.headers['x-session-id'];
    
    if (!sessionId) {
      return res.status(401).json({ error: 'Session ID required' });
    }

    const redisClient = getRedisClient();
    const sessionData = await redisClient.get(`session:${sessionId}`);
    
    if (!sessionData) {
      return res.status(401).json({ error: 'Invalid or expired session' });
    }

    req.user = JSON.parse(sessionData);
    next();
  } catch (error) {
    console.error('❌ Session verification error:', error);
    res.status(500).json({ error: 'Authentication failed' });
  }
};

// Create new game
router.post('/create', verifySession, async (req, res) => {
  try {
    const { gameMode = 'vs_human' } = req.body; // vs_human or vs_ai
    
    const response = await axios.post(`${GAME_ENGINE_URL}/api/game/create`, {
      created_by: req.user.userId,
      created_by_username: req.user.username,
      game_mode: gameMode
    });

    console.log(`🎮 Game created: ${response.data.gameId} by ${req.user.username}`);
    
    res.json(response.data);
  } catch (error) {
    console.error('❌ Game creation error:', error);
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: 'Failed to create game' });
    }
  }
});

// Join existing game
router.post('/join/:gameId', verifySession, async (req, res) => {
  try {
    const { gameId } = req.params;
    
    const response = await axios.post(`${GAME_ENGINE_URL}/api/game/join/${gameId}`, {
      player_id: req.user.userId,
      player_username: req.user.username
    });

    console.log(`🔗 ${req.user.username} joined game: ${gameId}`);
    
    res.json(response.data);
  } catch (error) {
    console.error('❌ Game join error:', error);
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: 'Failed to join game' });
    }
  }
});

// Make a move
router.post('/move/:gameId', verifySession, async (req, res) => {
  try {
    const { gameId } = req.params;
    const { position } = req.body;
    
    if (typeof position !== 'number' || position < 0 || position > 8) {
      return res.status(400).json({ error: 'Invalid position. Must be 0-8.' });
    }

    const response = await axios.post(`${GAME_ENGINE_URL}/api/game/move/${gameId}`, {
      player_id: req.user.userId,
      position
    });

    console.log(`🎯 Move made in game ${gameId}: position ${position} by ${req.user.username}`);
    
    res.json(response.data);
  } catch (error) {
    console.error('❌ Move error:', error);
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: 'Failed to make move' });
    }
  }
});

// Get game state
router.get('/state/:gameId', verifySession, async (req, res) => {
  try {
    const { gameId } = req.params;
    
    const response = await axios.get(`${GAME_ENGINE_URL}/api/game/state/${gameId}`);
    
    res.json(response.data);
  } catch (error) {
    console.error('❌ Get game state error:', error);
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: 'Failed to get game state' });
    }
  }
});

// Get list of active games
router.get('/list', verifySession, async (req, res) => {
  try {
    const response = await axios.get(`${GAME_ENGINE_URL}/api/game/list`);
    
    res.json(response.data);
  } catch (error) {
    console.error('❌ Get games list error:', error);
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: 'Failed to get games list' });
    }
  }
});

module.exports = router;