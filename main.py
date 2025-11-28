"""
LLM Analysis Quiz Solver - Main API Endpoint
"""
import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
import uvicorn
from quiz_solver import QuizSolver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Analysis Quiz Solver")

# Configuration
SECRET = os.getenv("QUIZ_SECRET", "your-secret-here")
EMAIL = os.getenv("QUIZ_EMAIL", "your-email@example.com")
TIMEOUT_SECONDS = 180  # 3 minutes


class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str
    # Allow other fields
    class Config:
        extra = "allow"


class QuizResponse(BaseModel):
    correct: bool
    url: Optional[str] = None
    reason: Optional[str] = None


@app.get("/")
async def root():
    return {"status": "online", "message": "LLM Analysis Quiz Solver API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/quiz")
async def handle_quiz(request: Request):
    """
    Main endpoint to receive quiz tasks and solve them.
    """
    try:
        # Parse JSON body
        try:
            body = await request.json()
        except Exception as e:
            logger.error(f"Invalid JSON: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate request
        try:
            quiz_request = QuizRequest(**body)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid request: {e}")
        
        # Verify secret
        if quiz_request.secret != SECRET:
            logger.warning(f"Invalid secret attempt from {quiz_request.email}")
            raise HTTPException(status_code=403, detail="Invalid secret")
        
        # Verify email matches
        if quiz_request.email != EMAIL:
            logger.warning(f"Email mismatch: {quiz_request.email} != {EMAIL}")
            raise HTTPException(status_code=403, detail="Email mismatch")
        
        logger.info(f"Received quiz request for URL: {quiz_request.url}")
        
        # Initialize quiz solver
        solver = QuizSolver(
            email=quiz_request.email,
            secret=quiz_request.secret,
            timeout_seconds=TIMEOUT_SECONDS
        )
        
        # Solve the quiz
        # Note: This runs synchronously to ensure quiz is solved within 3 minutes
        # The endpoint returns 200 after secret verification, then solves the quiz
        try:
            result = await solver.solve_quiz(quiz_request.url)
            return JSONResponse(content=result, status_code=200)
        except Exception as e:
            logger.error(f"Error solving quiz: {e}", exc_info=True)
            return JSONResponse(
                content={
                    "error": "Failed to solve quiz",
                    "reason": str(e)
                },
                status_code=500
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


