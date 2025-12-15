import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

import logging
from redis import Redis
from rq import Worker, Queue
from dotenv import load_dotenv
from src.config import Settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run the RQ worker"""
    try:
        settings = Settings.from_env()
        redis_url = settings.redis.url
        
        logger.info(f"Connecting to Redis at {settings.redis.host}:{settings.redis.port}")
        
        # Connect to Redis
        conn = Redis.from_url(redis_url)
        
        # Listen on default queue
        listen = ['default']
        
        logger.info("Worker started, listening on queues: " + ", ".join(listen))
        
        # Initialize queues with explicit connection
        queues = [Queue(name, connection=conn) for name in listen]
        
        # Initialize worker with explicit connection
        worker = Worker(queues, connection=conn)
        worker.work()
            
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
