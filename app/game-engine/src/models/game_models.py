from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum

class GameMode(str, Enum):
    VS_HUMAN = "vs_human"
    VS_AI = "vs_ai"

class GameStatus(str, Enum):
    WAITING = "waiting"      # Waiting for second player
    ACTIVE = "active"        # Game in progress
    FINISHED = "finished"    # Game completed
    ABANDONED = "abandoned"  # Game abandoned

class PlayerSymbol(str, Enum):
    X = "X"
    O = "O"

class HealthResponse(BaseModel):
    status: str
    service: str
    message: str

class Player(BaseModel):
    user_id: str
    username: str
    symbol: PlayerSymbol
    is_ai: bool = False

class GameState(BaseModel):
    game_id: str
    board: List[Optional[str]] = Field(default_factory=lambda: [None] * 9)
    players: List[Player] = []
    current_turn: Optional[str] = None  # user_id of current player
    status: GameStatus = GameStatus.WAITING
    winner: Optional[str] = None  # user_id of winner, or "draw"
    game_mode: GameMode = GameMode.VS_HUMAN
    created_at: datetime
    updated_at: datetime
    moves_count: int = 0

class CreateGameRequest(BaseModel):
    created_by: str
    created_by_username: str
    game_mode: GameMode = GameMode.VS_HUMAN

class JoinGameRequest(BaseModel):
    player_id: str
    player_username: str

class MoveRequest(BaseModel):
    player_id: str
    position: int = Field(ge=0, le=8, description="Board position (0-8)")

class GameResponse(BaseModel):
    success: bool
    message: str
    game_state: Optional[GameState] = None

class GameListResponse(BaseModel):
    success: bool
    games: List[GameState]

class MoveResponse(BaseModel):
    success: bool
    message: str
    game_state: GameState
    is_game_over: bool = False
    winner: Optional[str] = None
    ai_move: Optional[dict] = None  # If AI made a move after player