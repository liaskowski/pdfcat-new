import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker
import concurrent.futures
import logging
from typing import Callable, Any
from .config import settings

logger = logging.getLogger(__name__)

# --- 1. Broker Setup ---
if settings.TASK_MODE == "SERVER" and settings.REDIS_URL:
    logger.info(f"Using REDIS BROKER at {settings.REDIS_URL}")
    broker = RedisBroker(url=settings.REDIS_URL)
    dramatiq.set_broker(broker)
else:
    logger.info("Using THREAD POOL for tasks (Local Mode)")
    # StubBroker is mainly for testing, but we can use it as a placeholder.
    # However, for Local Mode, we won't actually use Dramatiq's dispatching mechanism
    # directly, but rather a wrapper that executes in a ThreadPool.
    # We still set a StubBroker to prevent Dramatiq errors if decorators are used.
    broker = StubBroker()
    dramatiq.set_broker(broker)


# --- 2. Local Executor (for Single PC mode) ---
_local_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


# --- 3. Task Decorator / Wrapper ---
def task(actor_name: str = None, queue_name: str = "default", priority: int = 0):
    """
    Hybrid Task Decorator.
    - If SERVER mode: Wraps with @dramatiq.actor
    - If LOCAL mode: Returns a wrapper that submits to ThreadPool
    """
    def decorator(func: Callable):
        if settings.TASK_MODE == "SERVER" and settings.REDIS_URL:
            # Server Mode: Use real Dramatiq actor
            return dramatiq.actor(actor_name=actor_name, queue_name=queue_name, priority=priority)(func)
        else:
            # Local Mode: Use ThreadPool wrapper
            def wrapper(*args, **kwargs):
                logger.info(f"Submitting local task: {func.__name__}")
                _local_executor.submit(func, *args, **kwargs)
            
            # Mimic Dramatiq's .send() method for compatibility
            wrapper.send = wrapper
            return wrapper
            
    return decorator
