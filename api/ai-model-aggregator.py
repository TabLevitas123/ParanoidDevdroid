# services/ai_model_aggregator.py

from typing import Dict, List, Optional, Any, Union
import asyncio
from datetime import datetime
import json

from config.constants import API_CONFIG
from config.settings import Settings
from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions
from services.pricing_manager import PricingManager
from services.model_selector import ModelSelector

# Import API integrations
from services.api_integration.openai_api import OpenAIAPI
from services.api_integration.anthropic_api import AnthropicAPI
from services.api_integration.stability_ai_api import StabilityAIAPI
from services.api_integration.eleven_labs_api import ElevenLabsAPI

logger = CustomLogger("ai_model_aggregator", "ai_services.log")
settings = Settings.get_settings()

class AIModelAggregator:
    def __init__(self, pricing_manager: PricingManager):
        self.pricing_manager = pricing_manager
        self.model_selector = ModelSelector()
        
        # Initialize API clients
        self.api_clients = {
            'openai': OpenAIAPI(),
            'anthropic': AnthropicAPI(),
            'stability': StabilityAIAPI(),
            'elevenlabs': ElevenLabsAPI()
        }
        
        # Cache for model capabilities and performance metrics
        self.model_cache: Dict[str, Dict[str, Any]] = {}
        self.performance_metrics: Dict[str, Dict[str, float]] = {}
        
        # Request tracking
        self.active_requests: Dict[str, asyncio.Task] = {}
        self.request_history: List[Dict[str, Any]] = []

    @handle_exceptions
    async def process_request(
        self,
        request_type: str,
        parameters: Dict[str, Any],
        user_id: str,
        max_retries: int = 3,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process an AI request through the appropriate service"""
        
        # Validate request type and parameters
        self._validate_request(request_type, parameters)
        
        # Select optimal model based on request type and parameters
        selected_model = await self.model_selector.select_model(
            request_type,
            parameters,
            self.performance_metrics
        )
        
        # Calculate estimated cost
        estimated_cost = await self.pricing_manager.estimate_cost(
            selected_model,
            parameters
        )
        
        # Create request record
        request_id = await self._create_request_record(
            user_id,
            request_type,
            selected_model,
            parameters,
            estimated_cost
        )
        
        # Process request with retries
        for attempt in range(max_retries):
            try:
                api_client = self._get_api_client(selected_model)
                
                # Start request processing
                processing_task = asyncio.create_task(
                    api_client.process_request(
                        request_type=request_type,
                        parameters=parameters,
                        timeout=timeout or API_CONFIG[selected_model['provider']]['timeout']
                    )
                )
                
                self.active_requests[request_id] = processing_task
                result = await processing_task
                
                # Update metrics and complete request record
                await self._update_metrics(selected_model, result)
                await self._complete_request_record(
                    request_id,
                    result,
                    estimated_cost
                )
                
                return {
                    'request_id': request_id,
                    'result': result,
                    'model_used': selected_model,
                    'cost': await self.pricing_manager.calculate_actual_cost(
                        selected_model,
                        result
                    )
                }
                
            except Exception as e:
                logger.error(f"Request attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    await self._fail_request_record(request_id, str(e))
                    raise CustomException(
                        "API_001",
                        "Request processing failed after retries",
                        {
                            "request_id": request_id,
                            "error": str(e)
                        }
                    )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    @handle_exceptions
    async def cancel_request(self, request_id: str, user_id: str) -> bool:
        """Cancel an active request"""
        if request_id not in self.active_requests:
            raise CustomException(
                "API_003",
                "Request not found or already completed",
                {"request_id": request_id}
            )
            
        task = self.active_requests[request_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            await self._cancel_request_record(request_id)
            return True
            
        return False

    def _validate_request(self, request_type: str, parameters: Dict[str, Any]) -> None:
        """Validate request type and parameters"""
        valid_request_types = {
            'text_generation',
            'text_completion',
            'image_generation',
            'speech_synthesis',
            'embedding'
        }
        
        if request_type not in valid_request_types:
            raise CustomException(
                "API_004",
                "Invalid request type",
                {
                    "request_type": request_type,
                    "valid_types": list(valid_request_types)
                }
            )
            
        required_params = {
            'text_generation': {'prompt', 'max_tokens'},
            'text_completion': {'prompt', 'max_tokens'},
            'image_generation': {'prompt', 'size'},
            'speech_synthesis': {'text'},
            'embedding': {'text'}
        }
        
        missing_params = required_params[request_type] - set(parameters.keys())
        if missing_params:
            raise CustomException(
                "API_005",
                "Missing required parameters",
                {"missing": list(missing_params)}
            )

    def _get_api_client(self, model: Dict[str, str]):
        """Get appropriate API client for the selected model"""
        provider = model['provider']
        if provider not in self.api_clients:
            raise CustomException(
                "API_006",
                "Unsupported API provider",
                {"provider": provider}
            )
        return self.api_clients[provider]

    async def _create_request_record(
        self,
        user_id: str,
        request_type: str,
        selected_model: Dict[str, str],
        parameters: Dict[str, Any],
        estimated_cost: float
    ) -> str:
        """Create and store request record"""
        request_record = {
            'request_id': f"req_{datetime.utcnow().timestamp()}",
            'user_id': user_id,
            'request_type': request_type,
            'model': selected_model,
            'parameters': parameters,
            'estimated_cost': estimated_cost,
            'status': 'processing',
            'start_time': datetime.utcnow().timestamp(),
            'end_time': None,
            'actual_cost': None,
            'error': None
        }
        
        self.request_history.append(request_record)
        return request_record['request_id']

    async def _complete_request_record(
        self,
        request_id: str,
        result: Dict[str, Any],
        actual_cost: float
    ) -> None:
        """Update request record on completion"""
        for record in self.request_history:
            if record['request_id'] == request_id:
                record.update({
                    'status': 'completed',
                    'end_time': datetime.utcnow().timestamp(),
                    'actual_cost': actual_cost,
                    'result': result
                })
                break

    async def _fail_request_record(self, request_id: str, error: str) -> None:
        """Update request record on failure"""
        for record in self.request_history:
            if record['request_id'] == request_id:
                record.update({
                    'status': 'failed',
                    'end_time': datetime.utcnow().timestamp(),
                    'error': error
                })
                break

    async def _cancel_request_record(self, request_id: str) -> None:
        """Update request record on cancellation"""
        for record in self.request_history:
            if record['request_id'] == request_id:
                record.update({
                    'status': 'cancelled',
                    'end_time': datetime.utcnow().timestamp()
                })
                break

    async def _update_metrics(
        self,
        model: Dict[str, str],
        result: Dict[str, Any]
    ) -> None:
        """Update performance metrics for the model"""
        model_id = f"{model['provider']}/{model['model']}"
        
        if model_id not in self.performance_metrics:
            self.performance_metrics[model_id] = {
                'success_rate': 0.0,
                'avg_latency': 0.0,
                'request_count': 0
            }
            
        metrics = self.performance_metrics[model_id]
        
        # Update success rate
        success = result.get('success', False)
        total_requests = metrics['request_count'] + 1
        metrics['success_rate'] = (
            (metrics['success_rate'] * metrics['request_count'] + (1 if success else 0))
            / total_requests
        )
        
        # Update average latency
        if 'latency' in result:
            metrics['avg_latency'] = (
                (metrics['avg_latency'] * metrics['request_count'] + result['latency'])
                / total_requests
            )
            
        metrics['request_count'] = total_requests

    async def get_model_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current status and metrics for all models"""
        status = {}
        for provider, client in self.api_clients.items():
            try:
                api_status = await client.check_status()
                models = await client.list_models()
                
                status[provider] = {
                    'status': api_status,
                    'available_models': models,
                    'metrics': {
                        model_id: self.performance_metrics.get(f"{provider}/{model_id}", {})
                        for model_id in models
                    }
                }
            except Exception as e:
                logger.error(f"Failed to get status for {provider}: {str(e)}")
                status[provider] = {
                    'status': 'error',
                    'error': str(e)
                }
                
        return status

    async def get_request_history(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get request history with optional filters"""
        filtered_history = self.request_history
        
        if user_id:
            filtered_history = [
                req for req in filtered_history
                if req['user_id'] == user_id
            ]
            
        if status:
            filtered_history = [
                req for req in filtered_history
                if req['status'] == status
            ]
            
        return filtered_history[offset:offset + limit]

    def __str__(self) -> str:
        active_count = len(self.active_requests)
        return f"AIModelAggregator(active_requests={active_count})"

    def __repr__(self) -> str:
        return (f"AIModelAggregator(providers={list(self.api_clients.keys())}, "
                f"active_requests={len(self.active_requests)})")
