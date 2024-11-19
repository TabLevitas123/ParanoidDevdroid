# main.py

import asyncio
import os
from typing import Dict, Any, Optional
from datetime import datetime
import signal
import sys
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from config.settings import Settings
from config.database_manager import DatabaseManager
from utils.logger import CustomLogger
from utils.error_handler import CustomException
from utils.validation_utils import Validator
from utils.encryption_manager import EncryptionManager

from tokens.token_manager import TokenManager
from tokens.dynamic_stabilizer import DynamicStabilizer
from agents.agent_manager import AgentManager
from marketplace.marketplace_core import MarketplaceCore
from marketplace.agent_listing import AgentListing
from marketplace.transaction_manager import TransactionManager
from services.ai_model_aggregator import AIModelAggregator
from services.pricing_manager import PricingManager
from users.user_manager import UserManager
from users.wallet_manager import WalletManager
from users.user_interface import UserInterface

logger = CustomLogger("main", "application.log")

class ApplicationManager:
    """Main application manager"""
    def __init__(self):
        self.settings = Settings.get_settings()
        self.app = FastAPI(
            title="AI Agent Platform",
            description="Decentralized AI-driven platform with marketplace",
            version="1.0.0"
        )
        
        # Core components
        self.db_manager: Optional[DatabaseManager] = None
        self.encryption_manager: Optional[EncryptionManager] = None
        self.validator: Optional[Validator] = None
        
        # Service managers
        self.token_manager: Optional[TokenManager] = None
        self.dynamic_stabilizer: Optional[DynamicStabilizer] = None
        self.agent_manager: Optional[AgentManager] = None
        self.marketplace: Optional[MarketplaceCore] = None
        self.agent_listing: Optional[AgentListing] = None
        self.transaction_manager: Optional[TransactionManager] = None
        self.ai_model_aggregator: Optional[AIModelAggregator] = None
        self.pricing_manager: Optional[PricingManager] = None
        self.user_manager: Optional[UserManager] = None
        self.wallet_manager: Optional[WalletManager] = None
        self.user_interface: Optional[UserInterface] = None
        
        # State tracking
        self.is_initialized = False
        self.is_shutting_down = False
        self.startup_time: Optional[datetime] = None
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Performance metrics
        self.metrics = {
            'requests_processed': 0,
            'errors_encountered': 0,
            'average_response_time': 0.0,
            'uptime_seconds': 0
        }

    async def initialize(self) -> None:
        """Initialize all application components"""
        try:
            logger.info("Initializing application...")
            
            # Initialize core components
            self.db_manager = DatabaseManager(
                self.settings.DATABASE_URL,
                pool_size=20,
                max_overflow=10
            )
            await self.db_manager.initialize()
            
            self.encryption_manager = EncryptionManager()
            self.validator = Validator()
            
            # Initialize service managers
            self.token_manager = TokenManager(
                self.db_manager,
                self.encryption_manager
            )
            
            self.dynamic_stabilizer = DynamicStabilizer(
                self.token_manager
            )
            
            self.agent_manager = AgentManager(
                self.token_manager,
                self.db_manager
            )
            
            self.marketplace = MarketplaceCore(
                self.token_manager,
                self.agent_manager
            )
            
            self.agent_listing = AgentListing(
                self.validator
            )
            
            self.transaction_manager = TransactionManager(
                self.token_manager,
                self.agent_manager,
                self.validator
            )
            
            self.pricing_manager = PricingManager()
            
            self.ai_model_aggregator = AIModelAggregator(
                self.pricing_manager
            )
            
            self.user_manager = UserManager(
                self.token_manager,
                self.encryption_manager,
                self.settings.SECRET_KEY.get_secret_value()
            )
            
            self.wallet_manager = WalletManager(
                self.token_manager,
                self.encryption_manager,
                self.settings.WEB3_PROVIDER
            )
            
            self.user_interface = UserInterface(
                self.user_manager,
                self.wallet_manager,
                self.token_manager
            )
            
            # Setup API routes
            self._setup_routes()
            
            # Setup middleware
            self._setup_middleware()
            
            # Start health check
            self.health_check_task = asyncio.create_task(
                self._health_check_loop()
            )
            
            self.is_initialized = True
            self.startup_time = datetime.utcnow()
            logger.info("Application initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Application initialization failed: {str(e)}")
            raise

    def _setup_routes(self) -> None:
        """Setup API routes"""
        # Health check endpoint
        @self.app.get("/health")
        async def health_check():
            return await self.check_health()
        
        # Mount service routers
        self.app.include_router(
            self.user_interface.app,
            prefix="/api",
            tags=["users"]
        )
        
        # Error handlers
        @self.app.exception_handler(CustomException)
        async def custom_exception_handler(request, exc):
            return {
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request, exc):
            logger.error(f"Unhandled exception: {str(exc)}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred"
                }
            }

    def _setup_middleware(self) -> None:
        """Setup application middleware"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Request timing middleware
        @self.app.middleware("http")
        async def add_timing_middleware(request, call_next):
            start_time = datetime.utcnow()
            response = await call_next(request)
            
            # Update metrics
            self.metrics['requests_processed'] += 1
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics['average_response_time'] = (
                (self.metrics['average_response_time'] * 
                 (self.metrics['requests_processed'] - 1) +
                 processing_time) / self.metrics['requests_processed']
            )
            
            return response

    async def _health_check_loop(self) -> None:
        """Periodic health check loop"""
        while not self.is_shutting_down:
            try:
                health_status = await self.check_health()
                if not health_status['status'] == 'healthy':
                    logger.warning(f"Unhealthy status detected: {health_status}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                await asyncio.sleep(5)  # Shorter sleep on error

    async def check_health(self) -> Dict[str, Any]:
        """Check health of all components"""
        if not self.is_initialized:
            return {
                'status': 'initializing',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        try:
            # Check database
            db_health = await self.db_manager.health_check()
            
            # Calculate uptime
            uptime = (datetime.utcnow() - self.startup_time).total_seconds()
            self.metrics['uptime_seconds'] = uptime
            
            return {
                'status': 'healthy' if db_health['status'] == 'healthy' else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'uptime': uptime,
                'components': {
                    'database': db_health,
                    'token_manager': self.token_manager.get_metrics(),
                    'agent_manager': self.agent_manager.get_metrics(),
                    'marketplace': self.marketplace.get_metrics(),
                    'user_manager': self.user_manager.get_metrics()
                },
                'metrics': self.metrics
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }

    async def shutdown(self) -> None:
        """Graceful shutdown of all components"""
        logger.info("Initiating application shutdown...")
        self.is_shutting_down = True
        
        # Cancel health check
        if self.health_check_task:
            self.health_check_task.cancel()
            
        try:
            # Shutdown components in reverse order
            if self.user_interface:
                await self.user_interface.cleanup()
                
            if self.wallet_manager:
                await self.wallet_manager.cleanup()
                
            if self.user_manager:
                await self.user_manager.cleanup()
                
            if self.ai_model_aggregator:
                await self.ai_model_aggregator.cleanup()
                
            if self.transaction_manager:
                await self.transaction_manager.cleanup()
                
            if self.marketplace:
                await self.marketplace.cleanup()
                
            if self.agent_manager:
                await self.agent_manager.cleanup()
                
            if self.token_manager:
                await self.token_manager.cleanup()
                
            if self.db_manager:
                await self.db_manager.cleanup()
                
            logger.info("Application shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            raise

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}")
            asyncio.create_task(self.shutdown())
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

# Application instance
app_manager = ApplicationManager()

# Startup event
@app_manager.app.on_event("startup")
async def startup_event():
    await app_manager.initialize()

# Shutdown event
@app_manager.app.on_event("shutdown")
async def shutdown_event():
    await app_manager.shutdown()

# Get FastAPI application instance
app = app_manager.app

if __name__ == "__main__":
    # Setup signal handlers
    app_manager._setup_signal_handlers()
    
    # Run application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )
