from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="LLM Quiz Solver API")

# Load secrets from environment
SECRET_STRING = os.getenv("SECRET_STRING")
EMAIL = os.getenv("EMAIL")

# Validate environment variables are set
if not SECRET_STRING or not EMAIL:
    raise ValueError("SECRET_STRING and EMAIL must be set in .env file")


# Request model for validation
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
    Main endpoint to receive quiz tasks
    
    Expected JSON payload:
    {
        "email": "your-email@example.com",
        "secret": "your-secret-string",
        "url": "https://example.com/quiz-123"
    }
    
    Returns:
    - HTTP 200: Valid request, quiz solving initiated
    - HTTP 400: Invalid JSON payload
    - HTTP 403: Invalid secret
    """
    
    # Try to parse JSON
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
        logger.warning(f"Invalid secret provided for email: {quiz_request.email}")
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    # Verify email matches (optional security check)
    if quiz_request.email != EMAIL:
        logger.warning(f"Email mismatch: expected {EMAIL}, got {quiz_request.email}")
        raise HTTPException(status_code=403, detail="Invalid email")
    
    # Log successful validation
    logger.info(f"Valid request received for quiz URL: {quiz_request.url}")
    
    # TODO: In Phase 2-6, we'll add the actual quiz solving logic here
    # For now, just acknowledge receipt
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "received",
            "message": "Quiz task received successfully",
            "url": quiz_request.url,
            "note": "Quiz solving logic will be implemented in later phases"
        }
    )


@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {"status": "healthy"}
