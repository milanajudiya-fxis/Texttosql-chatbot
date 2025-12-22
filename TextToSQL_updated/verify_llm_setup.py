import os
import sys

# Mock environment variables to avoid real connections
os.environ["LLM_MODEL"] = "gpt-4o-mini"
os.environ["LLM_WITHOUT_REASONING_MODEL"] = "gpt-3.5-turbo"
os.environ["OPENAI_API_KEY"] = "sk-fake-key"
os.environ["DB_USER"] = "user"
os.environ["DB_PASSWORD"] = "pass"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_NAME"] = "testdb"

# Mock missing dependencies
sys.modules["bs4"] = MagicMock()
sys.modules["bs4.BeautifulSoup"] = MagicMock()

# Put src in path
sys.path.append("/home/palak/Desktop/Projects/TextToSQL_Main/Texttosql-chatbot/TextToSQL_updated")

from src.config import Settings
from src.core import LLMManager
from src.tools import SQLToolkit
from src.agents.nodes import AgentNodes
from unittest.mock import MagicMock

def verify_setup():
    print("Verifying setup...")
    
    # 1. Verify Settings
    settings = Settings.from_env()
    assert settings.llm_without_reasoning is not None
    print("Settings verified.")

    # 2. Verify LLMManager
    llm_manager = LLMManager(settings)
    llm_without_reasoning = llm_manager.get_model_without_reasoning()
    assert llm_without_reasoning is not None
    assert llm_without_reasoning.model_name == "gpt-3.5-turbo"
    print("LLMManager verified.")

    # 3. Verify SQLToolkit
    mock_db = MagicMock()
    toolkit = SQLToolkit(mock_db, llm_manager.get_model(), llm_without_reasoning)
    assert toolkit.llm_without_reasoning is not None
    print("SQLToolkit verified.")

    # 4. Verify AgentNodes
    nodes = AgentNodes(toolkit, "mysql", 3)
    assert nodes.llm_without_reasoning is not None
    print("AgentNodes verified.")
    
    print("ALL CHECKS PASSED")

if __name__ == "__main__":
    verify_setup()
