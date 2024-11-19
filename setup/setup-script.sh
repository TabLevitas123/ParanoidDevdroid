#!/bin/bash

# setup_dev.sh

echo "Setting up development environment..."

# Check for Python 3.8+
python3 --version
if [ $? -ne 0 ]; then
    echo "Python 3.8+ is required"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check PostgreSQL
echo "Checking PostgreSQL..."
pg_isready
if [ $? -ne 0 ]; then
    echo "PostgreSQL is not running"
    echo "Please start PostgreSQL service"
    exit 1
fi

# Create test database
echo "Creating test database..."
psql -U postgres -c "CREATE USER test_user WITH PASSWORD 'test_pass';"
psql -U postgres -c "CREATE DATABASE test_db OWNER test_user;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE test_db TO test_user;"

# Install and start Redis
echo "Checking Redis..."
redis-cli ping
if [ $? -ne 0 ]; then
    echo "Redis is not running"
    echo "Please start Redis service"
    exit 1
fi

# Install Ganache (local blockchain)
echo "Installing Ganache..."
npm install -g ganache-cli
# Start Ganache in background
ganache-cli > ganache.log 2>&1 &
GANACHE_PID=$!

# Create logs directory
mkdir -p logs

# Run database migrations
echo "Running database migrations..."
python -c "
from config.database_manager import DatabaseManager
from config.database_models import Base
import asyncio

async def run_migrations():
    db_manager = DatabaseManager('postgresql://test_user:test_pass@localhost:5432/test_db')
    await db_manager.initialize()
    await db_manager.cleanup()

asyncio.run(run_migrations())
"

# Run debug tests
echo "Running debug tests..."
python debug_setup.py

# Stop Ganache
kill $GANACHE_PID

echo "Setup complete! You can now run the application with:"
echo "python main.py"
