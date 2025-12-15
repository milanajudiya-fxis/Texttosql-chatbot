"""SQL toolkit wrapper"""

import logging
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class SQLToolkit:
    """Wrapper for SQL database toolkit"""

    def __init__(self, db: SQLDatabase, llm: ChatOpenAI):
        """Initialize SQL toolkit"""
        self.db = db
        self.llm = llm
        self.toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        self.available_tools = self.toolkit.get_tools()
        self._initialize_tools()

    def _initialize_tools(self) -> None:
        """Initialize individual tools"""
        self.get_schema_tool = next(
            (t for t in self.available_tools if t.name == "sql_db_schema"),
            None,
        )
        self.run_query_tool = next(
            (t for t in self.available_tools if t.name == "sql_db_query"),
            None,
        )
        self.list_tables_tool = next(
            (t for t in self.available_tools if t.name == "sql_db_list_tables"),
            None,
        )

        self.check_query_tool = next(
            (t for t in self.available_tools if t.name == "sql_db_query_checker"),
            None,
        )

        if not all([self.get_schema_tool, self.run_query_tool, self.list_tables_tool, self.check_query_tool]):
            logger.warning("Some tools could not be initialized")

    def get_all_tools(self):
        """Get all available tools"""
        return self.available_tools

    def get_schema_tool_obj(self):
        """Get schema tool"""
        return self.get_schema_tool

    def get_run_query_tool_obj(self):
        """Get query execution tool"""
        return self.run_query_tool

    def get_list_tables_tool_obj(self):
        """Get list tables tool"""
        logger.info("LIST TABLES TOOL: " + str(self.list_tables_tool))  
        return self.list_tables_tool
    
    def get_check_query_tool_obj(self):
        """Get check query tool"""
        return self.check_query_tool
