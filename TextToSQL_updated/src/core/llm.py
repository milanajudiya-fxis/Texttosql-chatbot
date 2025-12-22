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
        self.model_without_reasoning: ChatOpenAI = None
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
            logger.critical(f"Successfully initialized LLM: {self.settings.llm.model}")
            logger.critical(f"LLM reasoning effort: {self.settings.llm.reasoning_effort}")

            # Initialize LLM without reasoning
            if self.settings.llm_without_reasoning:
                logger.info(f"Initializing LLM without reasoning model: {self.settings.llm_without_reasoning.model}")
                self.model_without_reasoning = ChatOpenAI(
                    model=self.settings.llm_without_reasoning.model,
                    temperature=self.settings.llm_without_reasoning.temperature,
                    max_tokens=self.settings.llm_without_reasoning.max_tokens,
                    timeout=self.settings.llm_without_reasoning.timeout,
                    max_retries=self.settings.llm_without_reasoning.max_retries,
                    api_key=self.settings.llm_without_reasoning.api_key,
                    reasoning_effort=self.settings.llm_without_reasoning.reasoning_effort,
                )
                logger.critical(f"Successfully initialized LLM without reasoning: {self.settings.llm_without_reasoning.model}")
                logger.critical(f"LLM without reasoning reasoning effort: {self.settings.llm_without_reasoning.reasoning_effort}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
            raise

    def get_model(self) -> ChatOpenAI:
        """Get the LLM model instance"""
        return self.model

    def get_model_without_reasoning(self) -> ChatOpenAI:
        """Get the LLM model without reasoning instance"""
        return self.model_without_reasoning