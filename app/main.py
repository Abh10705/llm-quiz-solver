from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
import os
import logging
from contextlib import asynccontextmanager
import httpx

from app.browser import quiz_browser
from app.llm import quiz_solver

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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SECRET_STRING or not EMAIL:
    raise ValueError("SECRET_STRING and EMAIL must be set in .env file")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set in .env file")


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    await quiz_browser.start()
    yield
    logger.info("Shutting down application...")
    await quiz_browser.stop()


# Initialize FastAPI app
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
        "email": EMAIL,
        "llm_model": quiz_solver.model
    }


@app.post("/solve")
async def solve_quiz(request: Request):
    """Main endpoint to receive and solve quiz tasks"""
    
    # Parse JSON
    try:
        body = await request.json()
        logger.info(f"Received request for URL: {body.get('url', 'unknown')}")
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
        logger.warning("Invalid secret provided")
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    # Verify email
    if quiz_request.email != EMAIL:
        logger.warning("Email mismatch")
        raise HTTPException(status_code=403, detail="Invalid email")
    
    logger.info(f"✓ Valid request for quiz URL: {quiz_request.url}")
    
    try:
        # Step 1: Fetch the quiz page
        quiz_data = await quiz_browser.fetch_quiz_page(quiz_request.url)
        logger.info("✓ Quiz page fetched")
        
        # Step 2: Analyze quiz with LLM
        analysis = await quiz_solver.analyze_quiz(quiz_data['question'])
        logger.info(f"✓ Quiz analyzed - Type: {analysis['task_type']}")
        
        # Step 3: Solve the quiz (for now, only simple quizzes)
                # Step 3: Solve the quiz
        if analysis['task_type'] == 'web_scraping':
            logger.info("Using web scraping solver")
            answer = await quiz_solver.solve_with_scraping(
                quiz_data['question'], 
                analysis, 
                quiz_browser
            )
        elif 'csv' in quiz_data['question'].lower() or 'cutoff' in quiz_data['question'].lower():

        
            logger.info("Using CSV analysis solver")
            answer = await quiz_solver.solve_with_csv_analysis(
                quiz_data, 
                analysis, 
                quiz_browser
            )
        else:
            logger.info("Using simple solver")
            answer = await quiz_solver.solve_simple_quiz(quiz_data['question'], analysis)
        
        logger.info(f"✓ Answer generated: {answer}")



        # Step 4: Submit the answer
        submit_url = quiz_data['submit_url'] or analysis.get('submit_url')
        
        if not submit_url:
            raise Exception("Could not determine submit URL")
        
        if submit_url.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(quiz_request.url)
            submit_url = f"{parsed.scheme}://{parsed.netloc}{submit_url}"
            logger.info(f"Converted relative URL to: {submit_url}")
        
        # Prepare submission payload
        submission = {
            "email": quiz_request.email,
            "secret": quiz_request.secret,
            "url": quiz_request.url,
            "answer": answer
        }
        
        logger.info(f"Submitting answer to: {submit_url}")
        
        # Submit the answer
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(submit_url, json=submission)
            response_data = response.json()
        
        logger.info(f"✓ Submission response: {response_data}")
        
        # Return the result
        return JSONResponse(
            status_code=200,
            content={
                "status": "completed",
                "quiz_url": quiz_request.url,
                "task_type": analysis['task_type'],
                "answer_submitted": answer,
                "submission_response": response_data,
                "correct": response_data.get("correct"),
                "next_url": response_data.get("url")
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing quiz: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing quiz: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {
        "status": "healthy",
        "browser": "ready" if quiz_browser.browser else "not_initialized",
        "llm_model": quiz_solver.model
    }
