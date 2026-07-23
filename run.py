"""
Entry point for the Odili Truth Seeker Backend.

Usage:
    python run.py                  # default: host=0.0.0.0, port=8000
    uvicorn app.main:app --reload  # development with auto-reload
"""
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
