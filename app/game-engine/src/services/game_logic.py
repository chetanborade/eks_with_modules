import random
from typing import List, Optional, Tuple
from models.game_models import GameState, Player, PlayerSymbol, GameStatus, GameMode
from datetime import datetime

class TicTacToeLogic:
    """Simple game logic for Tic-Tac-Toe"""
    
    WINNING_COMBINATIONS = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]              # Diagonals
    ]

    @staticmethod
    def is_valid_move(board: List[Optional[str]], position: int) -> bool:
        """Check if a move is valid"""
        return 0 <= position <= 8 and board[position] is None

    @staticmethod
    def make_move(board: List[Optional[str]], position: int, symbol: str) -> List[Optional[str]]:
        """Make a move on the board"""
        new_board = board.copy()
        new_board[position] = symbol
        return new_board

    @staticmethod
    def check_winner(board: List[Optional[str]]) -> Optional[str]:
        """Check for winner"""
        for combo in TicTacToeLogic.WINNING_COMBINATIONS:
            if (board[combo[0]] == board[combo[1]] == board[combo[2]] 
                and board[combo[0]] is not None):
                return board[combo[0]]
        
        if all(cell is not None for cell in board):
            return "draw"
        
        return None

    @staticmethod
    def ai_move(board: List[Optional[str]]) -> int:
        """Simple AI - random move"""
        available = [i for i, cell in enumerate(board) if cell is None]
        return random.choice(available) if available else -1


class GameEngine:
    """Simple game management"""
    
    @staticmethod
    def create_game(game_id: str, creator_id: str, creator_username: str, 
                   game_mode: GameMode) -> GameState:
        """Create a new game"""
        creator = Player(
            user_id=creator_id,
            username=creator_username,
            symbol=PlayerSymbol.X,
            is_ai=False
        )
        
        players = [creator]
        status = GameStatus.WAITING
        
        if game_mode == GameMode.VS_AI:
            ai_player = Player(
                user_id="ai_player",
                username="AI",
                symbol=PlayerSymbol.O,
                is_ai=True
            )
            players.append(ai_player)
            status = GameStatus.ACTIVE
        
        return GameState(
            game_id=game_id,
            board=[None] * 9,
            players=players,
            current_turn=creator_id,
            status=status,
            game_mode=game_mode,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @staticmethod
    def join_game(game_state: GameState, player_id: str, 
                 player_username: str) -> Tuple[bool, str]:
        """Add player to game"""
        if game_state.status != GameStatus.WAITING or len(game_state.players) >= 2:
            return False, "Cannot join game"
        
        new_player = Player(
            user_id=player_id,
            username=player_username,
            symbol=PlayerSymbol.O,
            is_ai=False
        )
        
        game_state.players.append(new_player)
        game_state.status = GameStatus.ACTIVE
        game_state.updated_at = datetime.utcnow()
        
        return True, "Joined successfully"
    
    @staticmethod
    def make_move(game_state: GameState, player_id: str, 
                 position: int) -> Tuple[bool, str, Optional[dict]]:
        """Process a move"""
        if (game_state.status != GameStatus.ACTIVE or 
            game_state.current_turn != player_id or
            not TicTacToeLogic.is_valid_move(game_state.board, position)):
            return False, "Invalid move", None
        
        player = next((p for p in game_state.players if p.user_id == player_id), None)
        if not player:
            return False, "Player not found", None
        
        # Make player move
        game_state.board = TicTacToeLogic.make_move(game_state.board, position, player.symbol.value)
        game_state.moves_count += 1
        game_state.updated_at = datetime.utcnow()
        
        # Check winner
        winner = TicTacToeLogic.check_winner(game_state.board)
        if winner:
            game_state.status = GameStatus.FINISHED
            game_state.winner = winner
            return True, f"Game over! Winner: {winner}", None
        
        # AI move if vs AI
        other_player = next((p for p in game_state.players if p.user_id != player_id), None)
        if other_player and other_player.is_ai:
            ai_position = TicTacToeLogic.ai_move(game_state.board)
            if ai_position >= 0:
                game_state.board = TicTacToeLogic.make_move(game_state.board, ai_position, other_player.symbol.value)
                game_state.moves_count += 1
                
                ai_winner = TicTacToeLogic.check_winner(game_state.board)
                if ai_winner:
                    game_state.status = GameStatus.FINISHED
                    game_state.winner = ai_winner
                    return True, f"Game over! Winner: {ai_winner}", {"position": ai_position}
                
                return True, "Move successful", {"position": ai_position}
        else:
            # Switch turns for human vs human
            game_state.current_turn = other_player.user_id if other_player else player_id
        
        return True, "Move successful", None