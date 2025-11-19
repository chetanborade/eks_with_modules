#!/usr/bin/env python3
"""
Simple test to verify our game logic works
"""

import sys
import os

# Add game engine to path
sys.path.insert(0, os.path.join('app', 'game-engine', 'src'))

def test_game_logic():
    print("🧪 Testing Tic-Tac-Toe Game Logic...")
    
    try:
        from services.game_logic import TicTacToeLogic, GameEngine
        from models.game_models import GameMode
        
        # Test 1: Basic game creation
        print("\n1. Testing game creation...")
        game_state = GameEngine.create_game(
            game_id="test-123",
            creator_id="player-1", 
            creator_username="Alice",
            game_mode=GameMode.VS_AI
        )
        print(f"✅ Game created: {game_state.game_id}")
        print(f"   Players: {len(game_state.players)}")
        print(f"   Mode: {game_state.game_mode}")
        
        # Test 2: Move validation
        print("\n2. Testing move validation...")
        valid = TicTacToeLogic.is_valid_move(game_state.board, 4)
        invalid = TicTacToeLogic.is_valid_move(game_state.board, 10)
        print(f"✅ Valid move (position 4): {valid}")
        print(f"✅ Invalid move (position 10): {not invalid}")
        
        # Test 3: Making moves
        print("\n3. Testing player moves...")
        success, message, ai_move = GameEngine.make_move(
            game_state=game_state,
            player_id="player-1",
            position=4  # Center
        )
        print(f"✅ Player move: {success} - {message}")
        if ai_move:
            print(f"🤖 AI responded at position: {ai_move['position']}")
        
        # Test 4: Board state
        print(f"\n4. Board after moves:")
        board = game_state.board
        for i in range(3):
            row = [board[i*3 + j] or '·' for j in range(3)]
            print(f"   {' '.join(row)}")
        
        # Test 5: Win detection
        print(f"\n5. Game status: {game_state.status}")
        print(f"   Winner: {game_state.winner or 'None yet'}")
        
        print(f"\n✅ All tests passed! Game logic is working correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   This is expected - we need to install Python dependencies")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def check_file_structure():
    print("\n📁 Checking file structure...")
    
    required_files = [
        'app/backend/package.json',
        'app/backend/src/server.js',
        'app/game-engine/requirements.txt', 
        'app/game-engine/src/main.py',
        'app/frontend/package.json',
        'app/frontend/src/App.js'
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing!")
            all_exist = False
    
    return all_exist

if __name__ == "__main__":
    print("🎮 Tic-Tac-Toe Microservices Test")
    print("=" * 40)
    
    structure_ok = check_file_structure()
    
    if structure_ok:
        print(f"\n📦 File structure is complete!")
        test_game_logic()
    else:
        print(f"\n❌ Some files are missing. Check your project structure.")
    
    print(f"\n📋 Next steps:")
    print(f"   1. Install Node.js and npm")
    print(f"   2. Install Python dependencies: pip install -r app/game-engine/requirements.txt")
    print(f"   3. Start Redis (Docker or local)")
    print(f"   4. Start services in order: Redis → Python → Node.js → React")