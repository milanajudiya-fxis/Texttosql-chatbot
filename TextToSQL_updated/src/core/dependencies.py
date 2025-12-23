"""
Core dependency management module.
Implements Singleton pattern for heavy resources.
"""
import logging
from typing import Optional
from src.config import Settings
from src.core.database import DatabaseManager
from src.core.llm import LLMManager

logger = logging.getLogger(__name__)

# Singleton instances
_db_manager: Optional[DatabaseManager] = None
_llm_manager: Optional[LLMManager] = None

def get_db_manager() -> DatabaseManager:
    """
    Get or create the global DatabaseManager instance.
    """
    global _db_manager
    if _db_manager is None:
        logger.info("Initializing global DatabaseManager instance")
        settings = Settings.from_env()
        _db_manager = DatabaseManager(settings)
    return _db_manager

def get_llm_manager() -> LLMManager:
    """
    Get or create the global LLMManager instance.
    """
    global _llm_manager
    if _llm_manager is None:
        logger.info("Initializing global LLMManager instance")
        settings = Settings.from_env()
        _llm_manager = LLMManager(settings)
    return _llm_manager

    _db_manager = None
    _llm_manager = None
    _conversation_manager = None
    _twilio_client = None
    logger.info("Global dependencies reset")

_redis_client = None
_conversation_manager = None
_twilio_client = None

def get_conversation_manager():
    """
    Get or create the global ConversationManager instance.
    """
    global _conversation_manager
    if _conversation_manager is None:
        from src.core.conversation import ConversationManager
        logger.info("Initializing global ConversationManager instance")
        settings = Settings.from_env()
        _conversation_manager = ConversationManager(settings)
    return _conversation_manager

def get_twilio_client():
    """
    Get or create the global Twilio Client instance.
    """
    global _twilio_client
    if _twilio_client is None:
        from twilio.rest import Client
        logger.info("Initializing global Twilio Client instance")
        settings = Settings.from_env()
        _twilio_client = Client(
            settings.twilio.account_sid,
            settings.twilio.auth_token
        )
    return _twilio_client

_redis_client = None

def get_redis_client():
    """
    Get or create the global Redis client instance.
    """
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            logger.info("Initializing global Redis client instance")
            settings = Settings.from_env()
            # Use from_url to include password/host/port/db handling automatically
            # and ADD TIMEOUTS to prevent hanging
            _redis_client = redis.Redis.from_url(
                settings.redis.url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis client initialized and connected")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            _redis_client = None
    return _redis_client
