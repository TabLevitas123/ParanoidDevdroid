import asyncio
import random
import time
import logging
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_random_agent_id() -> str:
    """Generate a random agent ID for testing purposes."""
    return f"agent_{random.randint(1000, 9999)}"

async def simulate_workload(duration: int = 10):
    """Simulate a workload by generating requests for a given duration."""
    start_time = time.time()
    while time.time() - start_time < duration:
        agent_id = generate_random_agent_id()
        logger.info(f"Simulating workload for {agent_id}")
        # Simulate task execution with a random delay
        await asyncio.sleep(random.uniform(0.5, 2.0))
        logger.info(f"Task for {agent_id} completed.")

if __name__ == '__main__':
    asyncio.run(simulate_workload())
