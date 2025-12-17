"""Agent graph builder"""

import logging
from typing import Optional
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from src.tools import SQLToolkit
from .nodes import AgentNodes
import os
from langchain_core.runnables.graph import MermaidDrawMethod

logger = logging.getLogger(__name__)


class AgentGraphBuilder:
    """Builds and manages the agent graph"""

    def __init__(self, toolkit: SQLToolkit, db_dialect: str, conversation_manager=None, thread_id: Optional[str] = None):
        """Initialize graph builder
        
        Args:
            toolkit: SQL toolkit for database operations
            db_dialect: Database dialect
            conversation_manager: Optional ConversationManager for memory
            thread_id: Optional thread ID for conversation context
        """

        self.toolkit = toolkit
        self.db_dialect = db_dialect
        self.conversation_manager = conversation_manager
        self.thread_id = thread_id
        self.max_check_attempts = int(os.getenv('MAX_CHECK_ATTEMPTS', '2'))
        self.nodes = AgentNodes(
            toolkit, 
            db_dialect, 
            max_check_attempts=self.max_check_attempts,
            conversation_manager=conversation_manager,
            thread_id=thread_id,
           
        )
        self.graph = None
        self.agent = None
        self._build_graph()


    def _build_graph(self) -> None:
        """Build the agent graph"""
        builder = StateGraph(MessagesState)

        # Add nodes
        builder.add_node("fetch_conversation_history", self.nodes.fetch_conversation_history)
        builder.add_node("classify_query", self.nodes.classify_query)  # Classification node
        builder.add_node("answer_general", self.nodes.answer_general)  # General answer node
        builder.add_node("answer_from_previous_conversation", self.nodes.answer_from_previous_conversation)
        builder.add_node("web_search", self.nodes.web_search_node)  # Web search node
        builder.add_node("list_db_tables", self.nodes.list_tables) # List tables node
        builder.add_node("call_get_schema", self.nodes.call_get_schema_llm) # Call get schema node
        builder.add_node("get_schema", ToolNode([self.toolkit.get_schema_tool_obj()], name="get_schema")) # Get schema tool node for retrieving schema
        builder.add_node("init_retry_count", self.nodes.init_retry_count)
        builder.add_node("generate_query", self.nodes.generate_query) # Generate query node
        # builder.add_node("get_relevant_schema_and_generate_query", self.nodes.get_relevant_schema_and_generate_query)
        # builder.add_node("validate_query", ToolNode([self.toolkit.get_check_query_tool_obj()], name="validate_query")) # Decision node to continue or not
        builder.add_node("check_query", self.nodes.check_query)     
        # builder.add_node(
        #     "run_query",
        #     ToolNode([self.toolkit.get_run_query_tool_obj()], name="run_query"), # Run query tool node
        # )
        builder.add_node("run_custom_query", self.nodes.run_query_custom)
        builder.add_node("generate_response", self.nodes.generate_response) # Generate final response node

    
    
        # Start → classify first in 4 category and based on that which path need to follow(V3) 
        builder.add_edge(START, "fetch_conversation_history")
        builder.add_edge("fetch_conversation_history", "classify_query")
        builder.add_conditional_edges(
            "classify_query",
            lambda state: (
                "IN_DOMAIN_WITHIN_PREVIOUS_CONVERSATION"
                if "IN_DOMAIN_WITHIN_PREVIOUS_CONVERSATION" in state["messages"][-1].content.upper()
                else (
                    "IN_DOMAIN_DB_QUERY"
                    if "IN_DOMAIN_DB_QUERY" in state["messages"][-1].content.upper()
                    else (
                        "IN_DOMAIN_WEB_SEARCH"
                        if "IN_DOMAIN_WEB_SEARCH" in state["messages"][-1].content.upper()
                        else "OUT_OF_DOMAIN"
                    )
                )
            ),
            {
                "IN_DOMAIN_WITHIN_PREVIOUS_CONVERSATION": "answer_from_previous_conversation",
                "IN_DOMAIN_DB_QUERY": "list_db_tables",
                "IN_DOMAIN_WEB_SEARCH": "web_search",
                "OUT_OF_DOMAIN": "answer_general"
            }
        )
        builder.add_edge("answer_general", END)
        builder.add_edge("answer_from_previous_conversation", END)
        
        # Web search now ends after searching, no fallback to DB
        builder.add_edge("web_search", END)
        
        
        builder.add_edge("list_db_tables", "call_get_schema")
        builder.add_edge("call_get_schema", "get_schema")
        builder.add_edge("get_schema", "init_retry_count")
        builder.add_edge("init_retry_count", "generate_query")
        builder.add_edge("generate_query", "check_query")
        builder.add_conditional_edges(
        "check_query",
        self.nodes.should_continue,    
        {
            "VALID": "run_custom_query",
            "INVALID": "generate_query",
            "ERROR": "generate_response",    # More than 2 times Invalid
        }
    )
        builder.add_edge("run_custom_query", "generate_response")
        builder.add_edge("generate_response", END)
        self.agent = builder.compile()
        logger.info("Agent graph built successfully")

        # png_bytes = self.agent.get_graph().draw_mermaid_png(
        # draw_method=MermaidDrawMethod.PYPPETEER)
        # with open("agent_flow.png", "wb") as f:
        #     f.write(png_bytes)
        # logger.info("Agent graph built successfully")



    def get_agent(self):
        """Get the compiled agent"""
        return self.agent

    def stream(self, input_state, stream_mode="values"):
        """Stream agent execution"""
        return self.agent.stream(input_state, stream_mode=stream_mode)




































        #  simpler flow without classification (V1) ----------------------------
        # builder.add_edge(START, "list_tables")
        # builder.add_edge("list_tables", "call_get_schema")
        # builder.add_edge("call_get_schema", "get_schema")
        # builder.add_edge("get_schema", "generate_query")
        # builder.add_conditional_edges("generate_query", self.nodes.should_continue)
        # builder.add_edge("check_query", "run_query")
        # builder.add_edge("run_query", "generate_query")


        # Start → classify first (V2) --------------------------------------------
        # builder.add_edge(START, "classify_query")
        # builder.add_conditional_edges(
        #     "classify_query",
        #     lambda state: (
        #         "SICILIAN" if "SICILIAN" in state["messages"][-1].content.upper()
        #         else "GREETING"
        #     ),
        #     {
        #         "SICILIAN": "list_db_tables",
        #         "GREETING": "answer_general"
        #     }
        # )

        # builder.add_edge("answer_general", END)
        # builder.add_edge("list_db_tables", "call_get_schema")
        # builder.add_edge("call_get_schema", "get_schema")
        # builder.add_edge("get_schema", "init_retry_count")
        # builder.add_edge("init_retry_count", "generate_query")
        # builder.add_edge("generate_query", "check_query")
        # builder.add_conditional_edges(
        #     "check_query",
        #     self.nodes.should_continue,  
        # )
        # builder.add_edge("check_query", "run_query")
        # builder.add_edge("run_query", "generate_response")
        # builder.add_edge("generate_response", END)

        
