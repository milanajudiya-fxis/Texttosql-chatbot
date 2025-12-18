"""
API dependency module.
"""
from typing import Annotated
from fastapi import Depends
from src.core.dependencies import get_db_manager as get_core_db_manager
from src.core.dependencies import get_llm_manager as get_core_llm_manager
from src.core import DatabaseManager, LLMManager
from src.tools import SQLToolkit

# Dependency providers
def get_db_manager() -> DatabaseManager:
    return get_core_db_manager()

def get_llm_manager() -> LLMManager:
    return get_core_llm_manager()

def get_toolkit(
    db_manager: Annotated[DatabaseManager, Depends(get_db_manager)],
    llm_manager: Annotated[LLMManager, Depends(get_llm_manager)]
) -> SQLToolkit:
    """
    Get the SQLToolkit instance.
    We can cache this if it's stateless, but for now recreating it is cheap
    if the heavy lifting (DB/LLM initialization) is already done.
    """
    return SQLToolkit(db_manager.get_database(), llm_manager.get_model())
