"""Agent node functions"""

import json
import logging
from typing import Optional
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import MessagesState
from src.tools import SQLToolkit
from src.core.dependencies import get_redis_client
from src.prompts.system_prompts import get_generate_query_prompt, get_check_query_prompt, get_classify_query_prompt, get_general_answer_prompt, get_generate_natural_response_prompt, get_answer_from_previous_convo_prompt, get_web_search_prompt,get_website_qa_prompt
import time
from langgraph.graph import END
import requests
from bs4 import BeautifulSoup
import os
from langchain_core.tools import tool

logger = logging.getLogger(__name__)



class AgentNodes:
    """Agent node functions"""

    def __init__(self, toolkit: SQLToolkit, db_dialect: str, max_check_attempts: int,conversation_manager=None, thread_id: Optional[str] = None,):
        """Initialize agent nodes
        
        Args:
            toolkit: SQL toolkit for database operations
            db_dialect: Database dialect (mysql, postgresql, etc.)
            conversation_manager: Optional ConversationManager for memory
            thread_id: Optional thread ID for conversation context
        """
        self.toolkit = toolkit
        self.db_dialect = db_dialect
        self.llm = toolkit.llm
        self.llm_without_reasoning = toolkit.llm_without_reasoning
        self.conversation_manager = conversation_manager
        self.thread_id = thread_id
        self.max_check_attempts = max_check_attempts
        self.llm_call = 1
        self.user_query = ""

    def fetch_conversation_history(self, state: MessagesState):
        """Fetch last 15 conversation messages and prepend them before the current query."""
        start_time = time.time()
        logger.warning("************** FETCH CONVERSATION HISTORY ************** ")
        current_message = state["messages"][-1]
        new_messages = []
        if self.conversation_manager and self.thread_id:
            history = self.conversation_manager.get_last_messages(
                self.thread_id, limit=15
            )
            if history:
                logger.info(f"Loaded {len(history)} messages from conversation history")

                # Convert history to LangChain format
                for msg in history:
                    if msg["role"] == "user":
                        new_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        new_messages.append(AIMessage(content=msg["content"]))
        state["messages"] = new_messages
        logger.info(f"CURRENT USER QUERY: {current_message}")
        logger.critical(f"fetch conversation node completed in {time.time() - start_time:.2f} seconds")
        logger.info("---------------------"*4)
        return state
    
    # LLM CALL 01 
    def classify_query(self, state: MessagesState):
        """Classify whether query is related to database or general question."""
        import re
        start_time = time.time()
        logger.warning("************** CLASSIFY QUERY **************")
        logger.warning("LLM call:" + str(self.llm_call))
        
        messages = state["messages"]
        # 3. EXTRACT CURRENT QUERY
        current_query = messages[-1].content
        self.user_query = current_query
        logger.warning(f"Current query: {current_query}")

        # --- GREETING BYPASS CHECK ---
        # Regex to match common greetings (case-insensitive)
        # Matches: "hi", "hello", "good morning", "whats app", "what's up", "hey", etc.
        greeting_pattern = r"^\s*(hi|hu|ho|hii+|hey+|heyy+|hello+|helo|good\s*(morning|afternoon|evening|day)|what'?s\s*(up|going\s*on|new)|how\s*(are|r)\s*(you|u)|howdy|yo+|sup|namaste|namaskar|bonjour|ciao|guten\s*tag|konnichiwa|ohayo|shalom)\s*[!.?]*\s*$"
        
        if re.match(greeting_pattern, current_query, re.IGNORECASE):
            logger.info(f"Greeting detected: {current_query}. Bypassing LLM classification.")
            logger.info("Directly routing to OUT_OF_DOMAIN (General Answer)")
            logger.critical(f"classify_query node completed in {time.time() - start_time:.2f} seconds")
            logger.info("---------------------"*4)
            # Create a mock AIMessage with the expected routing content
            return {"messages": [AIMessage(content="OUT_OF_DOMAIN")]}
        # -----------------------------

        self.llm_call += 1
        system_message = get_classify_query_prompt()
        previous_conversation = messages[1:-1] if len(messages) > 2 else []
        clean_previous_history = []
        if previous_conversation:
            for msg in previous_conversation:
                role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
                clean_previous_history.append({
                    "role": role,
                    "content": msg.content
                })
        
        llm_payload = {
            "system_message": system_message,
            "previous_conversation": clean_previous_history,
            "current_query": current_query
        }

        messages_for_llm = [
            {"role": "system", "content": llm_payload["system_message"]},
            {
                "role": "system",
                "content": f"PREVIOUS CONVERSATION:\n{json.dumps(llm_payload['previous_conversation'], indent=2)}"
            },
            {
                "role": "user",
                "content": llm_payload["current_query"]
            }
        ]
        llm = self.llm_without_reasoning
        logger.critical(f"llm --> gpt-4.1-mini")
        response = llm.invoke(messages_for_llm)
        decision = response.content.strip().upper()
        logger.info(f"Classification result: {decision}")
        logger.info(f"response content: {response}")
        logger.critical(f"classify_query node completed in {time.time() - start_time:.2f} seconds")
        logger.info("---------------------"*4)
        return {"messages": [response]}
    

    def scrape_and_cache_site(self):
        import os, time, requests, pytz
        from bs4 import BeautifulSoup
        from datetime import datetime

        BASE_URL = "https://siciliangames.com"
        PAGES = [
            "/index.php",
            "/schedule.php",
            "/standing.php",
            "/winners.php",
            "/contact.html"
        ]
        # Use fixed filename for reliable caching (mounted volume path)
        CACHE_FILE = "/app/src/sicilian_games_cache.html"
        MAX_AGE = 2 * 60 * 60  # 2 hours

        # ---------- Check existing cache ----------
        if os.path.exists(CACHE_FILE):
            file_age = time.time() - os.path.getmtime(CACHE_FILE)
            if file_age <= MAX_AGE:
                logger.info(f"Using cached file: {CACHE_FILE} (Age: {file_age:.0f}s)")
                return CACHE_FILE
            else:
                logger.info(f"Cache expired (Age: {file_age:.0f}s). Re-scraping...")
        else:
             logger.info("Cache file not found. Scraping...")

        # ---------- Scrape only if missing or expired ----------
        def clean_html(html):
            soup = BeautifulSoup(html, "html.parser")
            # Remove scripts, styles, etc.
            for tag in soup(["script", "style", "noscript", "iframe", "svg", "header", "footer"]):
                tag.decompose()
            
            # Return body content (preserving tags) or full html
            if soup.body:
                # prettify() can optionally be used, but str() is safer for raw content
                return str(soup.body)
            return str(soup)

        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist)

        sections = []
        logger.warning("Scraping website...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        for page in PAGES:
            try:
                url = BASE_URL + page
                # logger.info(f"Fetching {url}...")
                resp = requests.get(url, headers=headers, timeout=30)
                resp.raise_for_status()
                html_content = clean_html(resp.text)
                sections.append(f"<section id='{page}'><h2>Page: {page}</h2><div>{html_content}</div></section>")
            except Exception as e:
                logger.error(f"Failed to scrape {page}: {e}")
                sections.append(f"<section><h2>{page}</h2><p>CONTENT NOT AVAILABLE</p></section>")

        html = f"""
        <html>
        <head><title>Sicilian Games Cached Content</title></head>
        <body>
            <h1>Sicilian Games Website Content</h1>
            <p>Scraped at: {now_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
            {''.join(sections)}
        </body>
        </html>
        """

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        
        logger.info(f"Saved cache to {CACHE_FILE}")

        return CACHE_FILE

    def file_based_llm_node(self, state: MessagesState):
            import time

            start_time = time.time()
            logger.warning("************** FILE BASED NODE **************")

            user_query = self.user_query

            # 🔒 Will scrape ONLY if cache expired
            html_file = self.scrape_and_cache_site()
            
            messages = state["messages"]
            previous_conversation = messages[1:-1] if len(messages) > 2 else []
            clean_previous_history = []
            if previous_conversation:
                for msg in previous_conversation:
                    role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
                    clean_previous_history.append({
                        "role": role,
                        "content": msg.content
                    })

            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()

            system_prompt=get_website_qa_prompt()

            prompt = f"""
            {system_prompt}
        
            PREVIOUS CONVERSATION:
            {clean_previous_history}
            
            USER QUESTION:
            {user_query}

            WEBSITE CONTENT:
            {content}
            """

            response = self.llm.invoke(
                [{"role": "user", "content": prompt}]
            )

            answer = response.content

            if "NOT_FOUND" in answer:
                answer = "I’m unable to find the details right now.Please check back later or contact the Sicilian Games team.."
            logger.warning("Answer: " + answer)
            logger.critical(f"Node completed in {time.time() - start_time:.2f}s")

            return {
                "messages": [
                    AIMessage(
                        content=answer,
                        additional_kwargs={
                            "source": "file_cache",
                            "file": html_file
                        }
                    )
                ]
            }


    
    # LLM CALL 02_C
    def web_search_node(self, state: MessagesState):
        """
        Search strictly restricted to specific SicilianGames URLs.
        Uses Redis for caching scraped content.
        NO generic web search fallback.
        """
        start_time = time.time()
        logger.warning("**************  RESTRICTED WEB SEARCH NODE  ************** ")
        logger.warning("LLM call:" + str(self.llm_call))
        self.llm_call += 1

        user_query = self.user_query
        
        # 1. DIRECT URL MAPPING
        # Map topics to specific URLs
        direct_urls = {
            "schedule": "https://siciliangames.com/schedule.php",
            "winner": "https://siciliangames.com/winners.php",
            "sponsor": "https://siciliangames.com/index.php",
            "organizer": "https://siciliangames.com/index.php",
            "standings":"https://siciliangames.com/standing.php",
            "contact": "https://siciliangames.com/contact.html",
        }

        # Check if query matches any topic
        target_url = None
        for key, url in direct_urls.items():
            if key in user_query.lower():
                target_url = url
                break
        
        if not target_url:
            logger.warning(f"Query '{user_query}' did not match any allowed topics.")
            return {
                "messages": [
                    AIMessage(
                        content="I can only provide information about the schedule, winners, sponsors, organizers, standings, and contact details for Sicilian Games. Please ask about one of these topics.",
                        additional_kwargs={
                            "source": "restricted_web_search",
                            "status": "topic_not_allowed",
                            "query": user_query
                        }
                    )
                ]
            }

        logger.info(f"Targeting specific URL: {target_url}")
        
        try:
            # 2. CACHE CHECK
            redis_client = get_redis_client()
            cache_key = f"web_scrape:{target_url}"
            content_text = ""
            
            if redis_client:
                content_text = redis_client.get(cache_key)
            
            if content_text:
                logger.info("RETRIEVED URL CONTENT FROM CACHE")
            else:
                logger.info("FETCHING URL CONTENT DIRECTLY")
                try:
                    resp = requests.get(target_url, timeout=30)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    
                    # Remove script/style
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    content_text = soup.get_text(separator=' ', strip=True)
                    # Limit content size to avoid token overflow
                    content_text = " ".join(content_text.split()[:3000])
                    
                    # Cache the scraped text
                    if redis_client and content_text:
                        redis_client.setex(cache_key, 86400, content_text) # 24h cache
                        logger.info(f"Cached content for {target_url}")
                        
                except Exception as req_err:
                    logger.error(f"Failed to fetch URL {target_url}: {req_err}")
                    return {
                        "messages": [
                            AIMessage(
                                content=f"I'm sorry, I'm currently unable to access the {key} page. Please try again later.",
                                additional_kwargs={
                                    "source": "restricted_web_search",
                                    "error": str(req_err),
                                    "url": target_url
                                }
                            )
                        ]
                    }

            # 3. GENERATE ANSWER
            if content_text:
                logger.info("Generating Answer from Content")
                # Use a simplified prompt for summarization
                scrape_prompt = f"""
                You are a helpful assistant for Sicilian Games. 
                The user asked: "{user_query}"
                
                Here is the official information from {target_url}:
                {content_text}
                
                Answer the user's question using ONLY the provided content. 
                If the specific information is not in the text, say "I couldn't find that specific detail in the official {key} page."
                """
                
                # Using llm_without_reasoning for faster simple Q&A
                llm_response = self.llm_without_reasoning.invoke([{"role": "user", "content": scrape_prompt}])
                answer = llm_response.content
                
                logger.critical(f"restricted_web_search_node completed in {time.time() - start_time:.2f} seconds")
                logger.info("---------------------" * 4)

                return {
                    "messages": [
                        AIMessage(
                            content=answer,
                            additional_kwargs={
                                "source": "direct_scrape",
                                "url": target_url,
                                "query": user_query
                            }
                        )
                    ]
                }
            else:
                 # Should not happen if fetch was successful or cache hit
                 logger.error("Content text is empty after fetch/cache")
                 return {
                    "messages": [
                        AIMessage(
                            content="I couldn't retrieve the information at this time.",
                            additional_kwargs={"source": "restricted_web_search", "error": "empty_content"}
                        )
                    ]
                }

        except Exception as e:
            logger.error(f"Error during Restricted Web Search: {str(e)}")
            return {
                "messages": [
                    AIMessage(
                        content="An error occurred while verifying the information. Please try again.",
                        additional_kwargs={
                            "source": "restricted_web_search",
                            "error": str(e),
                            "query": user_query
                        }
                    )
                ]
            }

    # LLM CALL 02_A
    def answer_general(self, state: MessagesState):
        """Answer non-database related user questions normally."""
        import re
        start_time = time.time()
        logger.warning("************** GENERAL ANSWER **************")
        logger.warning("LLM call:" + str(self.llm_call))
        self.llm_call += 1
        user_msg = next(
            (msg for msg in reversed(state["messages"]) if msg.type == "human"),
            None
        )

        if not user_msg:
            logger.error("No human message found in state")
            return {"messages": []}

        # --- GREETING BYPASS & HARDCODED RESPONSE ---
        greeting_pattern = r"^\s*(hi|hello|hey|good\s*morning|good\s*afternoon|good\s*evening|what'?s\s*up|what'?s\s*app|namaste|hola|bonjour)\s*[!.?]*\s*$"
        
        if re.match(greeting_pattern, user_msg.content, re.IGNORECASE):
            greeting_response = (
                "👋 Hi! Welcome to Sicilian Games Info Bot\n\n"
                "I can help you with schedules, sports, standings, venues, partners, or quick updates.\n\n"
                "What would you like to check?"
            )
            logger.info("Greeting detected in answer_general. Returning hardcoded response.")
            logger.info(f"Greeting Content:\n{greeting_response}")
            logger.critical(f"answer_general node completed in {time.time() - start_time:.2f} seconds")
            logger.info("---------------------"*4)
            return {"messages": [AIMessage(content=greeting_response)]}
        # --------------------------------------------

        llm = self.llm_without_reasoning
        messages_for_llm = [
            {"role": "system", "content": 
             get_general_answer_prompt()},
            {"role": "user", "content": user_msg.content}
        ]
        response = llm.invoke(messages_for_llm)
        logger.info(f"User current message: {user_msg.content}")
        logger.info(f"General answer response: {response.content}")
        logger.critical(f"answer_general node completed in {time.time() - start_time:.2f} seconds")
        logger.info("---------------------"*4)
        return {"messages": [response]}
    
    # LLM CALL 02_B (SAME SYS PROMPT FOR ALL)
    def answer_from_previous_conversation(self, state: MessagesState):
        """Classify whether query is related to database or general question."""
        start_time = time.time()
        logger.warning("**************  ANSWER FROM PREVIOUS CONVO ************** ")
        logger.warning("LLM call:" + str(self.llm_call))
        self.llm_call += 1
        messages = state["messages"]
        system_message = get_answer_from_previous_convo_prompt()
        previous_conversation = messages[1:-1] if len(messages) > 2 else []
    
        clean_previous_history = []
        if previous_conversation:
            for msg in previous_conversation:
                role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
                clean_previous_history.append({
                    "role": role,
                    "content": msg.content
                })
        current_query = self.user_query
        logger.warning(f"Current query: {current_query}")
        llm_payload = {
            "system_message": system_message,
            "previous_conversation": clean_previous_history,
            "current_query": current_query
        }
        messages_for_llm = [
            {"role": "system", "content": llm_payload["system_message"]},
            {
                "role": "system",
                "content": f"PREVIOUS CONVERSATION:\n{json.dumps(llm_payload['previous_conversation'], indent=2)}"
            },
            {
                "role": "user",
                "content": llm_payload["current_query"]
            }
        ]
        llm = self.llm
        response = llm.invoke(messages_for_llm)

        
        logger.info(f"response content: {response}")
        logger.critical(f"classify_query node completed in {time.time() - start_time:.2f} seconds")
        logger.info("---------------------"*4)
        return {"messages": [response]}





    def list_tables(self, state: MessagesState):
        """List available tables and load conversation history if available"""
        messages = []
        start_time = time.time()
        logger.warning("************** LIST TABLE (MANUAL TOOL CALL) **************")
        table_list_tool_call = {
            "name": "sql_db_list_tables",
            "args": {"query": "" },
            "id": "sql_db_list_tables_1",
            "type": "tool_call",
        }
        # tool call message to indicate tool invocation
        tool_call_message = AIMessage(content="", tool_calls=[table_list_tool_call])
        tool_message = self.toolkit.get_list_tables_tool_obj().invoke(table_list_tool_call)
        response = AIMessage(content = tool_message.content)

        messages.append(response)
        logger.info(f"Tool Call  Message: {tool_call_message}")
        logger.info(f"Tool Message (Available tables): {tool_message.content}")
        logger.critical(f"list_tables node completed in {time.time() - start_time:.2f} seconds")
        logger.info("---------------------"*4)
        return {"messages": messages}
    
    def init_retry_count(self, state: MessagesState):
        state["retry_count"] = 0
        return {"messages": []}
  
    # LLM CALL 02_D
    def call_get_schema_llm(self, state: MessagesState):
        start_time = time.time()
        logger.warning("**************  RELAVANT TABLE FETCH (LLM TOOL CALL) ************** ")
        logger.warning("LLM call:" + str(self.llm_call))
        self.llm_call += 1
        llm = self.llm
        llm = llm.bind_tools([self.toolkit.get_schema_tool_obj()], tool_choice="any")
        response = llm.invoke(state["messages"])
        logger.info(f"GET Schema LLM Response: {response}")
        logger.critical(f"call_get_schema_llm node completed in {time.time() - start_time:.2f} seconds")
        logger.info("---------------------"*4)
        return {"messages": [response]}


    def call_get_schema(self, state: MessagesState):
        """Get database schema"""
        start_time = time.time()
        raw_tables = state["messages"][-1].content
        tool_input = {
            "table_names": raw_tables
        }
        tool_message = self.toolkit.get_schema_tool_obj().invoke(tool_input)
        response= AIMessage(content=tool_message)
        print("############################"*5)
        logger.info(f"GET Schema Response: {response}")
        logger.critical(f"call_get_schema node completed in {time.time() - start_time:.2f} seconds")
        print("############################"*5)
        return {"messages": [response]}
    
    



    # LLM CALL 03_D
    def generate_query(self, state: MessagesState):
        """Generate SQL query from natural language"""
        start_time = time.time()
        logger.warning("**************  GENERATE SQL QUERY ************** ")
        logger.warning("LLM call:" + str(self.llm_call))
        self.llm_call += 1
        system_message = {
            "role": "system",
            "content": get_generate_query_prompt(self.db_dialect) + "\n\nReturn ONLY a SQL query. No explanations.",
        }

        llm = self.llm_without_reasoning
        logger.critical(f"llm --> gpt-4.1-mini")
        response = llm.invoke([system_message] + state["messages"])
        logger.info(f"Dialect: {self.db_dialect}")
        logger.info(f"SCHEMA FOR GENERATING SQL--->{state['messages'][-1].content}")
        logger.info(f"Generated Query Response: {response}")
        logger.critical(f"generate_query node completed in {time.time() - start_time:.2f} seconds")
        logger.info("---------------------"*4)
        return {"messages": [response]}

    # LLM CALL 04_D ( Adding SQL in metadata )
    def check_query(self, state: MessagesState):
        """
        Validate SQL query WITHOUT calling any tool.
        Returns:
            - content: "VALID" or "INVALID"
            - metadata.sql_query: original SQL
        """
        start_time = time.time()
        logger.warning("**************  CHECK QUERY ************** ")
        logger.warning("LLM call:" + str(self.llm_call))
        self.llm_call += 1
        last_msg = state["messages"][-1]
        sql_query = last_msg.content.strip() if isinstance(last_msg.content, str) else None
        
        # IF SQL query is not available than return INVALID 
        if not sql_query:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "INVALID",
                    "metadata": {"sql_query": None}
                }]
            }
        system_message = {
            "role": "system",
            "content": get_check_query_prompt(self.db_dialect)
        }
        user_message = { "role": "user", "content": sql_query }
        llm = self.llm_without_reasoning
        logger.critical(f"llm --> gpt-4.1-mini")
        response = llm.invoke([system_message, user_message])
        verdict = response.content.strip().upper()
        logger.info(f"SQL Query for Validation: {sql_query}")
        logger.info(f"LLM Response: {response}")
        logger.info(f"Final verdict {verdict}")
        logger.critical(f"check query node completed in {time.time() - start_time:.2f} seconds")
        logger.info("---------------------"*4)

        if verdict.startswith("VALID"):
            verdict = "VALID"
        else:
            verdict = "INVALID"

        return {
            "messages": [{
                "role": "assistant",
                "content": verdict,              
                "metadata": {"sql_query": sql_query}  # KEEP SQL FOR next node
            }]
        }

    
    def should_continue(self, state: MessagesState):
        """
        Determine next step based on VALID/INVALID result
        and enforce max retry limit.
        """

        last_msg = state["messages"][-1]
        verdict = last_msg.content.strip().upper()
        logger.warning("**************  SHOULD CONTINUE ************** ")

        logger.warning(f"state: {state}")
        # Ensure retry counter exists
        if "retry_count" not in state:
            state["retry_count"] = 0
            
        logger.info(f"SHOULD_CONTINUE: Verdict='{verdict}', RetryCount={state['retry_count']}, Max={self.max_check_attempts}")

        if verdict == "VALID":
            state["retry_count"] = 0
            logger.info("SHOULD_CONTINUE: Decision=VALID")
            return "VALID"         

        if state["retry_count"] >= self.max_check_attempts:
            logger.info("SHOULD_CONTINUE: Decision=ERROR (Max retries reached)")
            return "ERROR"      

        state["retry_count"] += 1
        logger.info("SHOULD_CONTINUE: Decision=INVALID (Retrying)")
        return "INVALID"      

    def run_query_custom(self, state: MessagesState):
            """
            Execute SQL query WITHOUT tool calls.
            SQL is taken from metadata.sql_query (attached in check_query or generate_query).
            """
            start_time =  time.time()
            last_msg = state["messages"][-1]
            logger.warning("************** RUN QUERY ( TOOL CALL) **************")
            sql_query = None
            if hasattr(last_msg, "additional_kwargs"):
                metadata = last_msg.additional_kwargs.get("metadata", {})
                sql_query = metadata.get("sql_query")
            
            #  If no sql query found return 
            if not sql_query or not isinstance(sql_query, str):
                logger.info(f"SQL QUERY: {sql_query}")
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": "ERROR: No valid SQL query found in metadata.",
                        "metadata": {"sql_query": None}
                    }]
                }
            sql_query = sql_query.strip()

            #Hard safety: reject queries like VALID / INVALID
            if sql_query.upper() in ("VALID", "INVALID"):
                logger.info(f"SQL QUERY: {sql_query}")
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": "ERROR: Received 'VALID/INVALID' instead of SQL query.",
                        "metadata": {"sql_query": sql_query}
                    }]
        }

            run_tool = self.toolkit.get_run_query_tool_obj()
           
            try:
                result = run_tool.run({"query":sql_query})
                logger.info(f"SQL QUERY RESULT: {result}")
                logger.critical(f"run query node completed in {time.time() - start_time:.2f} seconds")

            except Exception as e:
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": f"ERROR executing SQL query: {str(e)}",
                        "metadata": {"sql_query": sql_query}
                    }]
                }

            return {
                "messages": [{
                    "role": "assistant",
                    "content": str(result),    # Pass raw result to generate_response
                    "metadata": {"sql_query": sql_query}
                }]
            }

    # LLM CALL 05_D
    def generate_response(self, state: MessagesState):
        """Generate final answer to user based on query results"""
        start_time = time.time()
        logger.warning("************** Generate Response ************** ")
        logger.warning("LLM call:" + str(self.llm_call))
        self.llm_call += 1
        system_message = {
            "role": "system",
            "content": get_generate_natural_response_prompt(),
        }

        llm = self.llm_without_reasoning
        logger.critical(f"llm --> gpt-4.1-mini")
        last_msg_obj = state["messages"][-1]
        last_msg_content = state["messages"][-1].content
        sql_query = None

        if hasattr(last_msg_obj, "additional_kwargs") and last_msg_obj.additional_kwargs:
            metadata = last_msg_obj.additional_kwargs.get("metadata", {})
            sql_query = metadata.get("sql_query")
        
        llm_messages =  [
                system_message,
                {"role": "user", "content": last_msg_content},
                {"role": "user", "content": sql_query},
                {"role": "user", "content": self.user_query}
        ] 


        response = llm.invoke(llm_messages)
        logger.info(f"SQL query: {sql_query}")
        logger.info(f"Executed SQL Query Result: {last_msg_content}")
        logger.info(f"original user question: {self.user_query}")
        logger.info(f"Generated final Response: {response}")
        logger.critical(f"generate response node completed in {time.time() - start_time:.2f} seconds")
        logger.info("---------------------"*4)
        return {"messages": [response]}
 

 















































































    # getting schema of the all tables listed in the previous node ( all db tables) (manual tool call)
    # def call_get_schema(self, state: MessagesState):
    #     """Get database schema"""
    #     start_time = time.time()
    #     raw_tables = state["messages"][-1].content
    #     tool_input = {
    #         "table_names": raw_tables
    #     }
    #     tool_message = self.toolkit.get_schema_tool_obj().invoke(tool_input)
    #     response= AIMessage(content=tool_message)
    #     print("############################"*5)
    #     logger.info(f"GET Schema Response: {response}")
    #     logger.critical(f"call_get_schema node completed in {time.time() - start_time:.2f} seconds")
    #     print("############################"*5)
    #     return {"messages": [response]}
    


    # def get_relevant_schema_and_generate_query(self, state: MessagesState):
    #     """Generate SQL query from natural language"""
    #     start_time = time.time()
    #     available_tables= state["messages"][-1].content 
    #     print("11111111111111111111111111111111111111111")
    #     print(available_tables)
    #     print("11111111111111111111111111111111111111111")

    #     system_message = {
    #         "role": "system",
    #         "content": get_generate_query_prompt(self.db_dialect, available_tables)
    #                 + "\n\nReturn ONLY a SQL query. No explanations.",
    #     }

    #     llm = self.llm.bind_tools([self.toolkit.get_schema_tool_obj()])
    #     response = llm.invoke([system_message] + state["messages"])
    #     logger.info("############ GENERATE SQL QUERY #####################################################################")
    #     logger.info("LLM call:" + str(self.llm_call))
    #     self.llm_call += 1
    #     logger.info(f"Dialect: {self.db_dialect}")
    #     logger.info(f"Generated Query Response: {response}")
    #     logger.info("-----------"*5)
    #     logger.info(state["messages"])
    #     logger.info("-----------"*5)
    #     logger.critical(f"generate_query node completed in {time.time() - start_time:.2f} seconds")
    #     logger.info("---------------------"*8)

    #     return {"messages": [response]}

































    # VERSION V2
    # def classify_query(self, state: MessagesState):
    #     """Classify whether query is related to database or general question."""
    #     start_time = time.time()
    #     logger.critical(f"classify_query node started at {start_time}")
    #     messages = state["messages"]

    #     # System message
    #     system_message = {
    #         "role": "system",
    #         "content": get_classify_query_prompt()
    #     }

    #     # Exclude the FIRST and LAST message from previous conversation
    #     previous_conversation = messages[1:-1] if len(messages) > 2 else []

    #     clean_previous_history = []

    #     if previous_conversation:   # Only loop when list is NOT empty
    #         for msg in previous_conversation:
    #             role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
                
    #             clean_previous_history.append({
    #                 "role": role,
    #                 "content": msg.content
    #             })
        
    #     print("previous_conversation", clean_previous_history)
    #     print("Current message", messages[-1].content)
    #     # Build LLM message list
    #     messages_for_llm = [
    #         system_message,
    #         {"role": "system", "content": "### PREVIOUS CONVERSATION ###"},
    #     ] + clean_previous_history + [
    #         {"role": "system", "content": "### CURRENT USER QUERY ###"},
    #         {"role": "user", "content": messages[-1].content},  
    #     ]
    #     print(";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;")
    #     print("MESSSSSSSSSSSSSSSSSSSSSSSSSSS", messages_for_llm)

    #     llm = self.llm
    #     response = llm.invoke(messages_for_llm)
    #     decision = response.content.strip().upper()
      
    #     logger.info("############ CLASSIFY QUERY ####################################################################")
    #     logger.info("LLM call:" + str(self.llm_call))
    #     self.llm_call += 1
    #     logger.info(f"Classification result: {decision}")
    #     logger.info(f"response content: {response}")
    #     logger.info(f"classify_query node completed in {time.time() - start_time:.2f} seconds")
    #     logger.info("############ CLASSIFY QUERY ###################################################################")
    #     return {"messages": [response]}



    # working with v2
    # def check_query(self, state: MessagesState):
    #     """Validate and check SQL query without tool calls (query is plain text)."""

    #     last_msg = state["messages"][-1]
    #     sql_query = last_msg.content.strip()
    #     if not sql_query:
    #         return {
    #             "messages": [{
    #                 "role": "assistant",
    #                 "content": "Invalid: No SQL query found."
    #             }]
    #         }

    #     # Build LLM validation prompt
    #     system_message = {
    #         "role": "system",
    #         "content": get_check_query_prompt(self.db_dialect),
    #     }

    #     user_message = {
    #         "role": "user",
    #         "content": sql_query
    #     }

    #     # LLM with run_query tool enabled for validation
    #     llm = self.llm.bind_tools(
    #         [self.toolkit.get_run_query_tool_obj()],
    #         tool_choice="any"
    #     )
    #     response = llm.invoke([system_message, user_message])
    #     response.id = last_msg.id
    #     return {"messages": [response]}

    # vorking with v2
    # def should_continue(self, state: MessagesState):
    #     """Determine if agent should continue or end (max 2 loops)"""

    #     # Initialize if missing
    #     if "retry_count" not in state:
    #         state["retry_count"] = 0

    #     # If last message has no tool call → end immediately
    #     last = state["messages"][-1]
    #     if not last.tool_calls:
    #         return END

    #     # If retry limit reached → end
    #     if state["retry_count"] >= self.max_check_attempts:
    #         return END

    #     # Otherwise continue and increment retry count
    #     state["retry_count"] += 1
    #     return "check_query"














































    # def check_query(self, state: MessagesState):
    #     """Validate and check SQL query"""
    #     start_time = time.time()
    #     system_message = {
    #         "role": "system",
    #         "content": get_check_query_prompt(self.db_dialect),
    #     }
    #     tool_call = state["messages"][-1].tool_calls[0]
    #     user_message = {"role": "user", "content": tool_call["args"]["query"]}

    #     llm = self.llm.bind_tools(
    #         [self.toolkit.get_run_query_tool_obj()], tool_choice="any"
    #     )
    #     response = llm.invoke([system_message, user_message])
    #     response.id = state["messages"][-1].id
    #     print("############################"*5)
    #     logger.info(f"Check Query Response: {response}")
    #     logger.critical(f"check_query node completed in {time.time() - start_time:.2f} seconds")
    #     print("############################"*5)
    #     return {"messages": [response]}




    # def should_continue_for_validation(self, state: MessagesState):
    #     """
    #     Decide next step after generate_query.
    #     If the LLM produced a tool call (SQL generation), continue to validate_query.
    #     If no tool call (meaning user said stop or query is final), end.
    #     """
    #     last = state["messages"][-1]

    #     # If LLM did not call a tool → nothing to validate → stop
    #     if not last.tool_calls:
    #         return END

    #     # If SQL was generated (tool call exists) → go validate
    #     return "validate_query"
    

    # def check_query(self, state: MessagesState):
    #     """Validate and check SQL query"""
    #     system_message = {
    #         "role": "system",
    #         "content": get_check_query_prompt(self.db_dialect),
    #     }
    #     tool_call = state["messages"][-1].tool_calls[0]
    #     user_message = {"role": "user", "content": tool_call["args"]["query"]}

    #     llm = self.llm.bind_tools(
    #         [self.toolkit.get_run_query_tool_obj()], tool_choice="any"
    #     )
    #     response = llm.invoke([system_message, user_message])
    #     response.id = state["messages"][-1].id
    #     return {"messages": [response]}




    # def check_query(self, state: MessagesState):
    #     """Validate the SQL query properly using manual tool call."""

    #     last = state["messages"][-1]
    #     print("############################"*5)
    #     print(f"Check Query Input Message: {last}")
    #     print("############################"*5)
    #     # No LLM tool call → INVALID
    #     if not last.tool_calls:
    #         return {"messages": [
    #             AIMessage(
    #                 content="Query validation result: INVALID",
    #                 additional_kwargs={"is_valid": False}
    #             )
    #         ]}

    #     sql_query = last.tool_calls[0]["args"].get("query")

    #     if not sql_query:
    #         return {"messages": [
    #             AIMessage(
    #                 content="Query validation result: INVALID",
    #                 additional_kwargs={"is_valid": False}
    #             )
    #         ]}
        
    #     print("############################"*5)
    #     logger.info(f"------>Validating SQL Query: {sql_query}")
    #     print("############################"*5)

    #     # --------------------------
    #     # 1️⃣ Build assistant tool_call
    #     # --------------------------
    #     validate_query_tool_call = {
    #         "name": "sql_db_query_checker",
    #         "args": {

    #             "query": sql_query
    #         },
    #         "id": "abc123",
    #         "type": "tool_call",
    #     }
    #     tool_call_message = AIMessage(content="", tool_calls=[validate_query_tool_call])
    #     tool_message = self.toolkit.get_check_query_tool_obj().invoke(validate_query_tool_call)
    #     print("############################"*5)
    #     logger.info(f"fffffffffffffffffffffffffffffffffffffffffffffffffffffff: {tool_message.content}")
    #     print("############################"*5)



    #     reponse = AIMessage(
    #         content=f"Query validation result: {tool_message.content}",
    #         additional_kwargs={"is_valid": tool_message.additional_kwargs.get("is_valid", False)}
    #     )
       

    #     return {
    #         "messages": [
    #             tool_call_message,  # assistant with tool_call
    #             tool_message,                 # tool response (role='tool')
    #             reponse                  # human readable assistant response
    #         ]
    #     }
    

    # def on_validation_result(self, state: MessagesState):
    #     """Return VALID or INVALID using the result produced by check_query()."""

    #     last = state["messages"][-1]

    #     # Prefer structured value from tool
    #     if last.additional_kwargs and "is_valid" in last.additional_kwargs:
    #         return "VALID" if last.additional_kwargs["is_valid"] else "INVALID"

    #     # Fallback based on text
    #     text = (last.content or "").lower()
    #     if "valid" in text and "invalid" not in text:
    #         return "VALID"

    #     return "INVALID"

