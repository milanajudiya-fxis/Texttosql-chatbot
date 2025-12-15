import logging
import json
import time
from twilio.rest import Client
from src.config import Settings
from src.core import DatabaseManager, LLMManager, ConversationManager
from src.tools import SQLToolkit
from src.agents import AgentGraphBuilder
from src.api.endpoints import split_message

# Configure logging
logger = logging.getLogger(__name__)

def send_whatsapp_message(to_number: str, message: str):
    """
    Send WhatsApp message using Twilio.
    Automatically splits messages >1600 chars.
    """
    try:
        logger.debug(f"Preparing to send WhatsApp message to {to_number}")
        
        settings = Settings.from_env()
        client = Client(
            settings.twilio.account_sid,
            settings.twilio.auth_token
        )

        message_parts = split_message(message)
        logger.debug(f"Message split into {len(message_parts)} chunk(s)")

        sids = []

        for part in message_parts:
            msg = client.messages.create(
                body=part,
                from_=settings.twilio.from_number,
                to=f"whatsapp:{to_number}"
            )
            sids.append(msg.sid)

        logger.info("WhatsApp message(s) sent successfully")
        return sids

    except Exception as e:
        logger.error(
            f"Error sending WhatsApp message to {to_number}: {e}",
            exc_info=True
        )
        return None

def process_whatsapp_message(body: str, from_number: str, to_number: str):
    """
    Background task to process WhatsApp message and send response.
    """
    start = time.time()
    try:
        logger.info(f"Processing background task for {from_number}: '{body[:100]}...'")
        
        # Load settings
        settings = Settings.from_env()
        
        # Initialize conversation manager
        conversation_manager = ConversationManager(settings)
        thread_id = from_number
        
        # Save user message
        conversation_manager.save_message(thread_id, "user", body)
        
        # Initialize components
        db_manager = DatabaseManager(settings)
        db = db_manager.get_database()
        dialect = db_manager.get_dialect()
        
        llm_manager = LLMManager(settings)
        llm = llm_manager.get_model()
        
        toolkit = SQLToolkit(db, llm)
        
        # Build agent
        agent_builder = AgentGraphBuilder(
            toolkit, 
            dialect,
            conversation_manager=conversation_manager,
            thread_id=thread_id
        )
        
        # Execute agent
        messages = []
        step_count = 0
        
        for step in agent_builder.stream(
            {"messages": [{"role": "user", "content": body}]},
            stream_mode="values",
        ):
            step_count += 1
            messages.append(step["messages"][-1])

        logger.info(f"Agent completed {step_count} steps")
        
        # Get response
        final_message = messages[-1] if messages else None
        result = final_message.content if final_message else "Sorry, I couldn't process your question."
        
        # Save assistant response
        conversation_manager.save_message(thread_id, "assistant", result)
        conversation_manager.close()
        
        # Send response via Twilio
        user_number = from_number.replace("whatsapp:", "")
        send_whatsapp_message(user_number, result)
        
        elapsed_time = time.time() - start
        logger.info(f"Task completed successfully in {elapsed_time:.2f}s")
        return True

    except Exception as e:
        elapsed_time = time.time() - start
        logger.error(f"Error in background task after {elapsed_time:.2f}s: {e}", exc_info=True)
        
        # Try to send error message
        try:
            user_number = from_number.replace("whatsapp:", "")
            send_whatsapp_message(user_number, "Sorry, I encountered an error processing your request.")
        except:
            pass
            
        return False
