"""LLM management module"""

import logging
from langchain_openai import ChatOpenAI
from src.config import Settings
import os

logger = logging.getLogger(__name__)


class LLMManager:
    """Manages LLM initialization and configuration"""

    def __init__(self, settings: Settings):
        """Initialize LLM manager"""
        logger.info("Initializing LLMManager")
        self.settings = settings
        self.model: ChatOpenAI = None
        self._initialize()
        logger.info("LLMManager initialized successfully")

    def _initialize(self) -> None:
        """Initialize the LLM model"""
        try:
            logger.info(f"Initializing LLM model: {self.settings.llm.model}")
            logger.debug(f"LLM Configuration - Temperature: {self.settings.llm.temperature}, Max Tokens: {self.settings.llm.max_tokens}, Timeout: {self.settings.llm.timeout}s")
            
            self.model = ChatOpenAI(
                model=self.settings.llm.model,
                temperature=self.settings.llm.temperature,
                max_tokens=self.settings.llm.max_tokens,
                timeout=self.settings.llm.timeout,
                max_retries=self.settings.llm.max_retries,
                api_key=self.settings.llm.api_key,
                reasoning_effort=self.settings.llm.reasoning_effort,
            
            )
            logger.info(f"Successfully initialized LLM: {self.settings.llm.model}")
            logger.info(f"LLM reasoning effort: {self.settings.llm.reasoning_effort}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
            raise

    def get_model(self) -> ChatOpenAI:
        """Get the LLM model instance"""
        return self.model