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

def reset_dependencies():
    """
    Reset global dependencies (useful for testing)
    """
    global _db_manager, _llm_manager
    _db_manager = None
    _llm_manager = None
    logger.info("Global dependencies reset")

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
            if settings.redis.password:
                _redis_client = redis.Redis(
                    host=settings.redis.host,
                    port=settings.redis.port,
                    db=settings.redis.db,
                    password=settings.redis.password,
                    decode_responses=True
                )
            else:
                _redis_client = redis.Redis(
                    host=settings.redis.host,
                    port=settings.redis.port,
                    db=settings.redis.db,
                    decode_responses=True
                )
            # Test connection
            _redis_client.ping()
            logger.info("Redis client initialized and connected")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            _redis_client = None
    return _redis_client
