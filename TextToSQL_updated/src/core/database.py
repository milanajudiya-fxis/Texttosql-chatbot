"""Database management module"""

import logging
from langchain_community.utilities import SQLDatabase
from src.config import Settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, settings: Settings):
        """Initialize database manager"""
        logger.info("Initializing DatabaseManager")
        self.settings = settings
        self.db: SQLDatabase = None
        self._connect()
        logger.info("DatabaseManager initialized successfully")

    def _connect(self) -> None:
        """Establish database connection"""
        try:
            logger.info(f"Attempting to connect to database: {self.settings.database.db_name}")
            self.db = SQLDatabase.from_uri(self.settings.database.uri)
            
            logger.info(f"Successfully connected to database: {self.settings.database.db_name}")
            logger.info(f"Database dialect: {self.db.dialect}")
            
            tables = self.db.get_usable_table_names()
            logger.info(f"Available tables ({len(tables)}): {', '.join(tables)}")
            logger.debug(f"Database URI: {self.settings.database.uri}")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}", exc_info=True)
            raise

    def get_database(self) -> SQLDatabase:
        """Get SQLDatabase instance"""
        return self.db

    def get_usable_tables(self) -> list[str]:
        """Get list of usable tables"""
        return self.db.get_usable_table_names()

    def get_dialect(self) -> str:
        """Get database dialect"""
        return self.db.dialect
