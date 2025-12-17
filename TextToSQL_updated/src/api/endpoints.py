"""FastAPI endpoints for Text-to-SQL service"""

import json
from fastapi import FastAPI, HTTPException, Form, Request
from pydantic import BaseModel
from typing import Optional
import logging
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import time
from redis import Redis
from rq import Queue
from src.config import Settings
from src.core import DatabaseManager, LLMManager, ConversationManager
from src.tools import SQLToolkit
from src.agents import AgentGraphBuilder

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Text-to-SQL API", version="1.0.0")

# Request/Response models
class QueryRequest(BaseModel):
    question: str
    thread_id: Optional[str] = None  # Optional thread ID for conversation memory
    
class QueryResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint"""
    logger.debug("Root endpoint called")
    return {"status": "ok", "message": "Text-to-SQL API is running"}


@app.get("/health")
async def health():
    """Detailed health check"""
    logger.debug("Health check endpoint called")
    return {
        "status": "healthy",
        "service": "Text-to-SQL API",
        "version": "1.0.0"
    }


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query and convert it to SQL.    
    Args:
        request: QueryRequest with the natural language question and optional thread_id
        
    Returns:
        QueryResponse with the result or error
    """
    start_time = time.time()
    try:
        logger.info(f"Processing query: {request.question[:100]}...")
        if request.thread_id:
            logger.info(f"Using thread_id: {request.thread_id}")
        
        # Load settings
        logger.debug("Loading application settings")
        settings = Settings.from_env()
        
        # Initialize conversation manager if thread_id is provided
        conversation_manager = None
        if request.thread_id:
            logger.info(f"Initializing conversation manager for thread: {request.thread_id}")
            conversation_manager = ConversationManager(settings)
            # Save user message
            conversation_manager.save_message(request.thread_id, "user", request.question)
            logger.debug("User message saved to conversation thread")
        
        # Initialize database
        logger.info("1: Initializing database manager")
        db_manager = DatabaseManager(settings)
        db = db_manager.get_database()
        dialect = db_manager.get_dialect()
        logger.debug(f"Database initialized with dialect: {dialect}")
        
        # Initialize LLM
        logger.info("2: Initializing LLM manager")
        llm_manager = LLMManager(settings)
        llm = llm_manager.get_model()
        logger.debug("LLM initialized and ready")
        
        # Initialize toolkit
        logger.info("3: Initializing SQL toolkit")
        toolkit = SQLToolkit(db, llm)
        logger.debug("SQL toolkit initialized with available tools")
        
        # Build agent graph with conversation memory
        logger.info("4: Building agent graph")
        agent_builder = AgentGraphBuilder(
            toolkit, 
            dialect, 
            conversation_manager=conversation_manager,
            thread_id=request.thread_id
        )
        logger.debug("Agent graph built successfully")
        
        # Collect the response
        logger.info("5: Executing agent stream")
        messages = []
        step_count = 0
        for step in agent_builder.stream(
            {"messages": [{"role": "user", "content": request.question}]},
            stream_mode="values",
        ):
            step_count += 1
            messages.append(step["messages"][-1])
            logger.debug(f"Agent step {step_count} completed")
        
        logger.info(f"Agent completed {step_count} steps")
        
        # Get the final response
        final_message = messages[-1] if messages else None
        result = final_message.content if final_message else "No response generated"
        logger.debug(f"Final response generated: {len(result)} characters")
        
        # Save assistant response if using conversation memory
        if conversation_manager and request.thread_id:
            conversation_manager.save_message(request.thread_id, "assistant", result)
            conversation_manager.close()
            logger.debug("Assistant response saved to conversation thread")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Query processed successfully in {elapsed_time:.2f}s")
        return QueryResponse(success=True, result=result)
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Error processing query after {elapsed_time:.2f}s: {e}", exc_info=True)
        return QueryResponse(success=False, error=str(e))


@app.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {
        "message": "Test endpoint working!",
        "endpoints": {
            "health": "/health",
            "query": "/query (POST)",
            "test": "/test",
            "whatsapp_webhook": "/webhook/whatsapp (POST)"
        }
    }



@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(None)
):
    """
    Twilio WhatsApp webhook endpoint with Redis Queue
    
    This endpoint receives incoming WhatsApp messages from Twilio,
    enqueues them for background processing, and returns immediately.
    """
    try:
        start_time = time.time()
        logger.info(f"Incoming message from {From}: '{Body[:100]}...'")
        
        # Load settings
        settings = Settings.from_env()
        
        # Connect to Redis
        redis_conn = Redis.from_url(settings.redis.url)
        q = Queue(connection=redis_conn)
        
        # Enqueue the task
        job = q.enqueue(
            'src.queue.tasks.process_whatsapp_message',
            args=(Body, From, To),
            job_timeout='5m'
        )
        
        logger.info(f"Task enqueued with ID: {job.id}")
        
        # Return immediate response to Twilio
        # We return an empty TwiML response so Twilio doesn't send anything back immediately
        # The worker will send the actual response asynchronously
        resp = MessagingResponse()
        logger.critical(f"Task enqueued successfully in {time.time() - start_time:.2f}s")
        return str(resp)
        
    except Exception as e:
        logger.error(f"Error enqueuing WhatsApp message: {e}", exc_info=True)
        
        # Send error message back to user immediately if enqueue fails
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an error receiving your message. Please try again.")
        return str(resp)
