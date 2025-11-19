from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

from config.redis_config import init_redis, get_redis_client
from routers import game_router
from models.game_models import HealthResponse

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Tic-Tac-Toe Game Engine",
    description="Python FastAPI service for game logic and AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    try:
        await init_redis()
        print("✅ Game Engine started successfully")
    except Exception as e:
        print(f"❌ Failed to start Game Engine: {e}")
        raise e

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return HealthResponse(
        status="healthy",
        service="tictactoe-game-engine",
        message="Game Engine is running"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    redis_client = get_redis_client()
    try:
        # Test Redis connection
        await redis_client.ping()
        redis_status = "connected"
    except:
        redis_status = "disconnected"
    
    return HealthResponse(
        status="healthy" if redis_status == "connected" else "degraded",
        service="tictactoe-game-engine",
        message=f"Game Engine is running - Redis: {redis_status}"
    )

# Include API routes
app.include_router(game_router.router, prefix="/api/game", tags=["game"])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=True if os.getenv("ENV") == "development" else False
    )