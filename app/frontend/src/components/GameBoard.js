import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function GameBoard({ user, onLogout }) {
  const [game, setGame] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const createGame = async (gameMode) => {
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(
        `${API_BASE}/api/game/create`,
        { gameMode },
        { headers: { 'X-Session-ID': user.sessionId } }
      );
      setGame(response.data.game_state);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create game');
    } finally {
      setLoading(false);
    }
  };

  const makeMove = async (position) => {
    if (!game || game.status !== 'active') return;

    try {
      const response = await axios.post(
        `${API_BASE}/api/game/move/${game.game_id}`,
        { position },
        { headers: { 'X-Session-ID': user.sessionId } }
      );
      setGame(response.data.game_state);
    } catch (err) {
      setError(err.response?.data?.error || 'Move failed');
    }
  };

  const renderBoard = () => {
    return (
      <div className="board">
        {game.board.map((cell, index) => (
          <button
            key={index}
            className={`cell ${cell ? 'filled' : ''}`}
            onClick={() => makeMove(index)}
            disabled={
              cell || 
              game.status !== 'active' || 
              game.current_turn !== user.userId
            }
          >
            {cell || ''}
          </button>
        ))}
      </div>
    );
  };

  const getGameStatus = () => {
    if (!game) return '';
    
    if (game.status === 'finished') {
      if (game.winner === 'draw') return '🤝 Game ended in a draw!';
      const winner = game.players.find(p => p.symbol === game.winner);
      return `🏆 ${winner?.username || game.winner} wins!`;
    }
    
    if (game.status === 'waiting') return '⏳ Waiting for another player...';
    
    const currentPlayer = game.players.find(p => p.user_id === game.current_turn);
    return game.current_turn === user.userId 
      ? '🎯 Your turn!' 
      : `⏳ ${currentPlayer?.username}'s turn`;
  };

  return (
    <div className="game-container">
      <div className="game-header">
        <button onClick={onLogout} className="logout-btn">Logout</button>
      </div>

      {!game ? (
        <div className="game-menu">
          <h2>Choose Game Mode</h2>
          <button 
            onClick={() => createGame('vs_ai')} 
            disabled={loading}
            className="game-mode-btn"
          >
            🤖 Play vs AI
          </button>
          <button 
            onClick={() => createGame('vs_human')} 
            disabled={loading}
            className="game-mode-btn"
          >
            👥 Play vs Human
          </button>
          {loading && <p>Creating game...</p>}
        </div>
      ) : (
        <div className="game-area">
          <div className="game-info">
            <p className="game-status">{getGameStatus()}</p>
            <div className="players">
              {game.players.map(player => (
                <span key={player.user_id} className="player">
                  {player.symbol}: {player.username}
                  {player.is_ai && ' 🤖'}
                </span>
              ))}
            </div>
          </div>
          
          {renderBoard()}
          
          <button 
            onClick={() => setGame(null)}
            className="new-game-btn"
          >
            🎮 New Game
          </button>
        </div>
      )}
      
      {error && <p className="error">{error}</p>}
    </div>
  );
}

export default GameBoard;