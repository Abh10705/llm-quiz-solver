from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
import os
import logging
from contextlib import asynccontextmanager

from app.browser import quiz_browser

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load secrets from environment
SECRET_STRING = os.getenv("SECRET_STRING")
EMAIL = os.getenv("EMAIL")

if not SECRET_STRING or not EMAIL:
    raise ValueError("SECRET_STRING and EMAIL must be set in .env file")


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize browser
    logger.info("Starting up application...")
    await quiz_browser.start()
    yield
    # Shutdown: Clean up browser
    logger.info("Shutting down application...")
    await quiz_browser.stop()


# Initialize FastAPI app with lifespan
app = FastAPI(title="LLM Quiz Solver API", lifespan=lifespan)


# Request model
class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "LLM Quiz Solver API is active",
        "email": EMAIL
    }


@app.post("/solve")
async def solve_quiz(request: Request):
    """
    Main endpoint to receive and solve quiz tasks
    """
    
    # Parse JSON
    try:
        body = await request.json()
        logger.info(f"Received request: {body}")
    except Exception as e:
        logger.error(f"Invalid JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Validate request structure
    try:
        quiz_request = QuizRequest(**body)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail="Missing required fields: email, secret, url")
    
    # Verify secret
    if quiz_request.secret != SECRET_STRING:
        logger.warning(f"Invalid secret provided")
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    # Verify email
    if quiz_request.email != EMAIL:
        logger.warning(f"Email mismatch")
        raise HTTPException(status_code=403, detail="Invalid email")
    
    logger.info(f"✓ Valid request for quiz URL: {quiz_request.url}")
    
    # Fetch and parse the quiz page
    try:
        quiz_data = await quiz_browser.fetch_quiz_page(quiz_request.url)
        
        logger.info(f"✓ Successfully fetched quiz")
        logger.info(f"  Question preview: {quiz_data['question'][:150]}...")
        logger.info(f"  Submit URL: {quiz_data['submit_url']}")
        
        # TODO Phase 3: Send question to LLM
        # TODO Phase 4-6: Process data and solve quiz
        # TODO: Submit answer to submit_url
        
        # For now, return the extracted quiz data
        return JSONResponse(
            status_code=200,
            content={
                "status": "quiz_fetched",
                "message": "Quiz page successfully fetched and parsed",
                "quiz_url": quiz_request.url,
                "submit_url": quiz_data['submit_url'],
                "question_preview": quiz_data['question'][:200],
                "note": "Quiz solving logic will be implemented in Phase 3-6"
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing quiz: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing quiz: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {"status": "healthy", "browser": "ready" if quiz_browser.browser else "not_initialized"}
