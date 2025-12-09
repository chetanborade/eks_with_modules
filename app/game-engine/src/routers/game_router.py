from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime

from models.game_models import (
    CreateGameRequest, JoinGameRequest, MoveRequest,
    GameResponse, GameListResponse, MoveResponse, GameState
)
from services.game_logic import GameEngine
from config.redis_config import store_game, get_game, get_all_games

router = APIRouter()

@router.post("/create", response_model=GameResponse)
async def create_game(request: CreateGameRequest):
    """Create a new game"""
    try:
        game_id = str(uuid.uuid4())
        
        # Create game using game engine
        game_state = GameEngine.create_game(
            game_id=game_id,
            creator_id=request.created_by,
            creator_username=request.created_by_username,
            game_mode=request.game_mode
        )
        
        # Store in Redis
        game_dict = game_state.model_dump(mode='json')
        # Convert datetime to string for JSON serialization
        game_dict['created_at'] = game_state.created_at.isoformat()
        game_dict['updated_at'] = game_state.updated_at.isoformat()
        
        success = await store_game(game_id, game_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store game")
        
        print(f"Game created: {game_id} by {request.created_by_username} ({request.game_mode})")
        
        return GameResponse(
            success=True,
            message=f"Game created successfully in {request.game_mode.value} mode",
            game_state=game_state
        )
        
    except Exception as e:
        print(f"Create game error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create game: {str(e)}")

@router.post("/join/{game_id}", response_model=GameResponse)
async def join_game(game_id: str, request: JoinGameRequest):
    """Join an existing game"""
    try:
        # Get game from Redis
        game_data = await get_game(game_id)
        if not game_data:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Convert back to GameState object
        game_data['created_at'] = datetime.fromisoformat(game_data['created_at'])
        game_data['updated_at'] = datetime.fromisoformat(game_data['updated_at'])
        game_state = GameState(**game_data)
        
        # Join the game
        success, message = GameEngine.join_game(
            game_state=game_state,
            player_id=request.player_id,
            player_username=request.player_username
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        # Update in Redis
        game_dict = game_state.model_dump(mode='json')
        game_dict['created_at'] = game_state.created_at.isoformat()
        game_dict['updated_at'] = game_state.updated_at.isoformat()
        
        await store_game(game_id, game_dict)
        
        print(f"{request.player_username} joined game: {game_id}")
        
        return GameResponse(
            success=True,
            message=message,
            game_state=game_state
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Join game error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to join game: {str(e)}")

@router.post("/move/{game_id}", response_model=MoveResponse)
async def make_move(game_id: str, request: MoveRequest):
    """Make a move in the game"""
    try:
        # Get game from Redis
        game_data = await get_game(game_id)
        if not game_data:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Convert back to GameState object
        game_data['created_at'] = datetime.fromisoformat(game_data['created_at'])
        game_data['updated_at'] = datetime.fromisoformat(game_data['updated_at'])
        game_state = GameState(**game_data)
        
        # Make the move
        success, message, ai_move_data = GameEngine.make_move(
            game_state=game_state,
            player_id=request.player_id,
            position=request.position
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        # Update in Redis
        game_dict = game_state.model_dump(mode='json')
        game_dict['created_at'] = game_state.created_at.isoformat()
        game_dict['updated_at'] = game_state.updated_at.isoformat()
        
        await store_game(game_id, game_dict)
        
        is_game_over = game_state.status.value == "finished"
        winner = game_state.winner if is_game_over else None
        
        print(f"Move made in {game_id}: position {request.position}")
        if ai_move_data:
            print(f"AI responded with position {ai_move_data['position']}")
        
        return MoveResponse(
            success=True,
            message=message,
            game_state=game_state,
            is_game_over=is_game_over,
            winner=winner,
            ai_move=ai_move_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Make move error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to make move: {str(e)}")

@router.get("/state/{game_id}", response_model=GameResponse)
async def get_game_state(game_id: str):
    """Get current game state"""
    try:
        # Get game from Redis
        game_data = await get_game(game_id)
        if not game_data:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Convert back to GameState object
        game_data['created_at'] = datetime.fromisoformat(game_data['created_at'])
        game_data['updated_at'] = datetime.fromisoformat(game_data['updated_at'])
        game_state = GameState(**game_data)
        
        return GameResponse(
            success=True,
            message="Game state retrieved",
            game_state=game_state
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get game state error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get game state: {str(e)}")

@router.get("/list", response_model=GameListResponse)
async def list_games():
    """Get list of all active games"""
    try:
        games_data = await get_all_games()
        games = []
        
        for game_data in games_data:
            try:
                # Convert datetime strings back to datetime objects
                game_data['created_at'] = datetime.fromisoformat(game_data['created_at'])
                game_data['updated_at'] = datetime.fromisoformat(game_data['updated_at'])
                game_state = GameState(**game_data)
                games.append(game_state)
            except Exception as e:
                print(f"⚠️ Skipping invalid game data: {e}")
                continue
        
        # Sort by creation time (newest first)
        games.sort(key=lambda x: x.created_at, reverse=True)
        
        return GameListResponse(
            success=True,
            games=games
        )
        
    except Exception as e:
        print(f"List games error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list games: {str(e)}")