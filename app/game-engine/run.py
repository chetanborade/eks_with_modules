#!/usr/bin/env python3

import sys
import os
import subprocess

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Start the FastAPI server"""
    port = os.getenv("PORT", "8000")
    env = os.getenv("ENV", "development")
    
    cmd = [
        "uvicorn", 
        "main:app", 
        "--host", "0.0.0.0", 
        "--port", port
    ]
    
    if env == "development":
        cmd.extend(["--reload"])
    
    print(f"🚀 Starting Game Engine on port {port}")
    print(f"📚 Environment: {env}")
    
    # Change to src directory
    os.chdir(os.path.join(os.path.dirname(__file__), 'src'))
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Game Engine stopped")

if __name__ == "__main__":
    main()