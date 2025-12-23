import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

import logging
from redis import Redis
from rq import Worker, Queue
from dotenv import load_dotenv
from colorlog import ColoredFormatter
from src.config import Settings

# Load environment variables
load_dotenv()

# Configure logging with colored formatter and pipe separator
formatter = ColoredFormatter(
    "%(log_color)s%(name)-15s | %(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s%(reset)s",
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False

# Also configure root logger for other modules
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()
root_logger.addHandler(handler)

def main():
    """Run the RQ worker"""
    try:
        settings = Settings.from_env()
        redis_url = settings.redis.url
        
        logger.info(f"Connecting to Redis at {settings.redis.host}:{settings.redis.port}")
        
        # Connect to Redis
        # conn = Redis.from_url(redis_url)
        conn = Redis.from_url(
            redis_url,
            socket_timeout=10,
            socket_connect_timeout=10,
            retry_on_timeout=True
        )

        
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
