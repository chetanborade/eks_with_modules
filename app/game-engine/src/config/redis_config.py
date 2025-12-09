import redis.asyncio as redis
import os
import json
from typing import Optional

redis_client: Optional[redis.Redis] = None

async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            health_check_interval=30
        )
        
        # Test connection
        await redis_client.ping()
        print(f"Game Engine Redis connected: {redis_url}")
        
    except Exception as e:
        print(f"Redis connection failed: {e}")
        raise e

def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    if redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return redis_client

async def store_game(game_id: str, game_data: dict) -> bool:
    """Store game state in Redis"""
    try:
        client = get_redis_client()
        await client.setex(f"game:{game_id}", 3600, json.dumps(game_data))  # 1 hour TTL
        return True
    except Exception as e:
        print(f"Failed to store game {game_id}: {e}")
        return False

async def get_game(game_id: str) -> Optional[dict]:
    """Retrieve game state from Redis"""
    try:
        client = get_redis_client()
        game_data = await client.get(f"game:{game_id}")
        
        if game_data:
            return json.loads(game_data)
        return None
    except Exception as e:
        print(f"Failed to get game {game_id}: {e}")
        return None

async def delete_game(game_id: str) -> bool:
    """Delete game from Redis"""
    try:
        client = get_redis_client()
        await client.delete(f"game:{game_id}")
        return True
    except Exception as e:
        print(f"Failed to delete game {game_id}: {e}")
        return False

async def get_all_games() -> list:
    """Get all active games"""
    try:
        client = get_redis_client()
        keys = await client.keys("game:*")
        games = []
        
        for key in keys:
            game_data = await client.get(key)
            if game_data:
                game = json.loads(game_data)
                games.append(game)
        
        return games
    except Exception as e:
        print(f"Failed to get games list: {e}")
        return []