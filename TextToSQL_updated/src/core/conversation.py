"""Conversation memory management module"""

import json
import time
import logging
import pymysql
from typing import List, Dict, Optional
from src.config import Settings

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation threads with persistent storage in MySQL"""

    def __init__(self, settings: Settings):
        """Initialize conversation manager
        
        Args:
            settings: Application settings containing database configuration
        """
        logger.info("Initializing ConversationManager")
        self.settings = settings
        self.conn = None
        self.table_name = "conversation_threads"
        self.memory_limit = 15  # Number of messages to keep in context
        self._connect()
        self._ensure_table_exists()
        logger.info("ConversationManager initialized successfully")

    def _connect(self) -> None:
        """Establish MySQL connection"""
        try:
            logger.info(f"Attempting to connect to MySQL at {self.settings.database.host}:{self.settings.database.port}")
            self.conn = pymysql.connect(
                host=self.settings.database.host,
                user=self.settings.database.user,
                password=self.settings.database.password,
                database=self.settings.database.db_name,
                port=self.settings.database.port,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(f"Successfully connected to MySQL database: {self.settings.database.db_name}")
            logger.debug(f"Connection charset: utf8mb4, Memory limit: {self.memory_limit} messages")
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}", exc_info=True)
            raise

    def _ensure_table_exists(self) -> None:
        """Create conversation_threads table if it doesn't exist"""
        try:
            logger.info(f"Ensuring table '{self.table_name}' exists")
            with self.conn.cursor() as cursor:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        thread_id VARCHAR(255) PRIMARY KEY,
                        conversation JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
            self.conn.commit()
            logger.info(f"Table '{self.table_name}' is ready for use")
            logger.debug(f"Table schema: thread_id (PK), conversation (JSON), created_at, updated_at")
        except Exception as e:
            logger.error(f"Failed to create table '{self.table_name}': {e}", exc_info=True)
            raise

    def get_last_messages(self, thread_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve last N messages from a conversation thread
        
        Args:
            thread_id: Unique identifier for the conversation thread
            limit: Number of messages to retrieve (default: self.memory_limit)
            
        Returns:
            List of message dictionaries with role, content, and timestamp
        """
        if limit is None:
            limit = self.memory_limit

        try:
            logger.debug(f"Retrieving last {limit} messages for thread_id: {thread_id}")
            with self.conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT conversation FROM {self.table_name} WHERE thread_id=%s",
                    (thread_id,)
                )
                row = cursor.fetchone()

                if row is None:
                    logger.info(f"No conversation found for thread_id: {thread_id}")
                    return []

                history = json.loads(row['conversation'])
                messages = history[-limit:] if len(history) > limit else history
                logger.info(f"Retrieved {len(messages)} messages from {len(history)} total for thread_id: {thread_id}")
                logger.debug(f"Message roles: {[m.get('role') for m in messages]}")
                return messages

        except Exception as e:
            logger.error(f"Error retrieving messages for thread_id {thread_id}: {e}", exc_info=True)
            return []

    def save_message(self, thread_id: str, role: str, content: str) -> None:
        """Save a message to the conversation thread
        
        Args:
            thread_id: Unique identifier for the conversation thread
            role: Message role (user, assistant, system)
            content: Message content
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            logger.debug(f"Saving {role} message to thread_id: {thread_id}")
            with self.conn.cursor() as cursor:
                # Check if thread exists
                cursor.execute(
                    f"SELECT conversation FROM {self.table_name} WHERE thread_id=%s",
                    (thread_id,)
                )
                row = cursor.fetchone()

                new_message = {
                    "role": role,
                    "content": content,
                    "timestamp": timestamp
                }

                if row is None:
                    # Create new thread
                    history = [new_message]
                    cursor.execute(
                        f"INSERT INTO {self.table_name} (thread_id, conversation) VALUES (%s, %s)",
                        (thread_id, json.dumps(history))
                    )
                    logger.info(f"Created new conversation thread: {thread_id}")
                    logger.debug(f"Initial message ({role}): {len(content)} characters")
                else:
                    # Append to existing thread
                    history = json.loads(row['conversation'])
                    history.append(new_message)

                    cursor.execute(
                        f"UPDATE {self.table_name} SET conversation=%s WHERE thread_id=%s",
                        (json.dumps(history), thread_id)
                    )
                    logger.info(f"Added {role} message to thread: {thread_id} (total messages: {len(history)})")
                    logger.debug(f"Message content length: {len(content)} characters")

            self.conn.commit()
            logger.debug(f"Transaction committed for thread_id: {thread_id}")

        except Exception as e:
            logger.error(f"Error saving message to thread {thread_id}: {e}", exc_info=True)
            logger.info(f"Rolling back transaction for thread_id: {thread_id}")
            self.conn.rollback()
            raise

    def create_thread(self, thread_id: str) -> None:
        """Create a new conversation thread
        
        Args:
            thread_id: Unique identifier for the conversation thread
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    f"INSERT IGNORE INTO {self.table_name} (thread_id, conversation) VALUES (%s, %s)",
                    (thread_id, json.dumps([]))
                )
            self.conn.commit()
            logger.info(f"Thread created: {thread_id}")
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            raise

    def thread_exists(self, thread_id: str) -> bool:
        """Check if a conversation thread exists
        
        Args:
            thread_id: Unique identifier for the conversation thread
            
        Returns:
            True if thread exists, False otherwise
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT 1 FROM {self.table_name} WHERE thread_id=%s",
                    (thread_id,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking thread existence: {e}")
            return False

    def get_thread_count(self) -> int:
        """Get total number of conversation threads
        
        Returns:
            Number of threads in the database
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) as count FROM {self.table_name}")
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Error getting thread count: {e}")
            return 0

    def close(self) -> None:
        """Close database connection"""
        if self.conn and self.conn.open:
            self.conn.close()
            logger.info("Closed conversation database connection")

    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.close()
        except:
            pass  # Silently ignore errors during cleanup
