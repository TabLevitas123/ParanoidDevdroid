# tests/test_app.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

app = FastAPI(title="AI Platform Test API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-11-16T12:00:00Z"}

@app.post("/api/users/register")
async def register_user(user_data: Dict[str, Any]):
    return {
        "success": True,
        "user": {
            "id": "test_user_id",
            "username": user_data["username"],
            "email": user_data["email"]
        }
    }

@app.post("/api/users/login")
async def login_user(login_data: Dict[str, Any]):
    return {
        "success": True,
        "token": "test_auth_token_123"
    }

@app.get("/api/users/profile")
async def get_profile():
    return {
        "id": "test_user_id",
        "username": "test_user",
        "email": "test@example.com"
    }

@app.post("/api/wallets")
async def create_wallet(wallet_data: Dict[str, Any]):
    return {
        "success": True,
        "wallet": {
            "id": "test_wallet_id",
            "name": wallet_data.get("name", "Test Wallet"),
            "balance": wallet_data.get("initial_balance", 0)
        }
    }

@app.post("/api/agents")
async def create_agent(agent_data: Dict[str, Any]):
    return {
        "success": True,
        "agent": {
            "id": "test_agent_id",
            "name": agent_data["name"],
            "description": agent_data.get("description", "")
        }
    }

# For test runner
def get_test_app():
    return app
