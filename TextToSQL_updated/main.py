"""Main entry point for the Text-to-SQL agent"""

import sys
import logging
from dotenv import load_dotenv
from src.config import Settings
from src.core import DatabaseManager, LLMManager
from src.tools import SQLToolkit
from src.agents import AgentGraphBuilder
from colorlog import ColoredFormatter

# Load environment variables from .env file
load_dotenv()

# Configure logging
formatter = ColoredFormatter(
    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'bold_red',
    }
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger("src.agents.nodes")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.propagate = False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python main.py \"your question here\"")
        return

    question = sys.argv[1]

    try:
        # Load settings
        settings = Settings.from_env()
        logger.info("Settings loaded")

        # Initialize database
        db_manager = DatabaseManager(settings)
        db = db_manager.get_database()
        dialect = db_manager.get_dialect()

        # Initialize LLM
        llm_manager = LLMManager(settings)
        llm = llm_manager.get_model()

        # Initialize toolkit
        toolkit = SQLToolkit(db, llm)
        logger.info("Toolkit initialized")

        # Build agent graph
        agent_builder = AgentGraphBuilder(toolkit, dialect)
        agent = agent_builder.get_agent()

        # Run agent
        logger.info("Running agent...")
        print("\n---- Running Agent ----\n")

        for step in agent_builder.stream(
            {"messages": [{"role": "user", "content": question}]},
            stream_mode="values",
        ):
            step["messages"][-1].pretty_print()

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
