const express = require('express');
const cors = require('cors');
require('dotenv').config();

const authRoutes = require('./routes/auth');
const gameRoutes = require('./routes/game');
const { initRedis } = require('./config/redis');

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'tictactoe-backend' });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/game', gameRoutes);

const PORT = process.env.PORT || 5000;

async function startServer() {
  try {
    await initRedis();
    console.log('✅ Redis connected');
    
    app.listen(PORT, () => {
      console.log(`🚀 Backend running on port ${PORT}`);
    });
  } catch (error) {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
  }
}

startServer();