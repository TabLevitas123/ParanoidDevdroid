# setup_env.py

import os

def setup_test_env():
    """Set up temporary environment variables for testing"""
    os.environ['DATABASE_URL'] = "sqlite:///./test.db"  # Use SQLite for quick testing
    os.environ['SECRET_KEY'] = "test_secret_key_12345"
    os.environ['ENVIRONMENT'] = "test"
    os.environ['WEB3_PROVIDER'] = "http://localhost:8545"
    
    # API keys (using dummy values for testing)
    os.environ['OPENAI_API_KEY'] = "test_openai_key"
    os.environ['ANTHROPIC_API_KEY'] = "test_anthropic_key"
    os.environ['STABILITY_API_KEY'] = "test_stability_key"
    os.environ['ELEVENLABS_API_KEY'] = "test_elevenlabs_key"

if __name__ == "__main__":
    setup_test_env()
    print("Test environment variables set")

    # Import and run tests
    import quick_test
    asyncio.run(quick_test.run_test())
