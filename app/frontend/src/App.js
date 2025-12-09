import React, { useState } from 'react';
import './App.css';
import Login from './components/Login';
import GameBoard from './components/GameBoard';

function App() {
  const [user, setUser] = useState(null);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Tic-Tac-Toe Battle</h1>
        {user ? (
          <p>Welcome, <strong>{user.username}</strong>!</p>
        ) : (
          <p>Enter your username to start playing</p>
        )}
      </header>
      
      <main>
        {!user ? (
          <Login onLogin={setUser} />
        ) : (
          <GameBoard user={user} onLogout={() => setUser(null)} />
        )}
      </main>
    </div>
  );
}

export default App;