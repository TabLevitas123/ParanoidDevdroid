# run_test.py

import asyncio
import logging
from setup_env import setup_test_env
from test_db_manager import init_test_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main test runner"""
    try:
        # Setup test environment
        setup_test_env()
        logger.info("Test environment setup complete")
        
        # Initialize test database
        db = await init_test_db()
        logger.info("Test database initialized")
        
        # Run quick tests
        from quick_test import run_test
        success = await run_test()
        
        if success:
            logger.info("All tests completed successfully!")
        else:
            logger.error("Some tests failed!")
            
    except Exception as e:
        logger.error(f"Test runner failed: {str(e)}")
        raise
    finally:
        # Cleanup
        await db.cleanup()
        logger.info("Test cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())
