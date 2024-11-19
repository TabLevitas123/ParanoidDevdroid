# run_all.py

import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def setup_environment():
    """Setup test environment"""
    try:
        logger.info("Setting up test environment...")
        
        # Create test directory if it doesn't exist
        Path("./test").mkdir(exist_ok=True)
        
        # Initialize database
        from init_db import init_db
        engine = await init_db("sqlite+aiosqlite:///./test/test.db")
        
        # Setup mock blockchain
        from mock_blockchain import mock_blockchain
        
        # Setup environment variables
        os.environ.update({
            'DATABASE_URL': "sqlite+aiosqlite:///./test/test.db",
            'SECRET_KEY': "test_secret_key_123",
            'ENVIRONMENT': "test",
            'DEBUG': "true"
        })
        
        logger.info("Environment setup complete")
        return engine
        
    except Exception as e:
        logger.error(f"Environment setup failed: {str(e)}")
        raise

async def run_tests():
    """Run all tests"""
    try:
        logger.info("Running tests...")
        
        # Run test harness
        from test_harness import TestHarness
        harness = TestHarness()
        await harness.setup()
        success = await harness.run_basic_tests()
        
        if success:
            logger.info("All tests passed!")
        else:
            logger.error("Some tests failed!")
        
        return success
        
    except Exception as e:
        logger.error(f"Tests failed: {str(e)}")
        return False

async def cleanup():
    """Cleanup test environment"""
    try:
        logger.info("Cleaning up test environment...")
        
        # Remove test database
        try:
            os.remove("./test/test.db")
        except FileNotFoundError:
            pass
        
        logger.info("Cleanup complete")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")

async def main():
    """Main execution flow"""
    try:
        # Setup
        engine = await setup_environment()
        
        # Run tests
        success = await run_tests()
        
        if success:
            # Start application if tests passed
            if input("Tests passed! Start application server? (y/n): ").lower() == 'y':
                import uvicorn
                from main import app
                
                logger.info("Starting application server...")
                uvicorn.run(
                    app,
                    host="0.0.0.0",
                    port=8000,
                    reload=True,
                    log_level="debug"
                )
        
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}")
        sys.exit(1)
        
    finally:
        await cleanup()

if __name__ == "__main__":
    asyncio.run(main())
