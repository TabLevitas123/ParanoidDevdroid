# services/api_integration/anthropic_api.py

import asyncio
from typing import Dict, List, Any, Optional
import time
from datetime import datetime
import aiohttp
import json

import anthropic
from anthropic import Anthropic, RateLimitError, APIError, APITimeoutError

from config.api_keys import APIKeyManager
from config.constants import API_CONFIG
from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions

logger = CustomLogger("anthropic_api", "anthropic_integration.log")

class AnthropicAPI:
    def __init__(self):
        self.api_key_manager = APIKeyManager()
        self.base_url = API_CONFIG['anthropic']['base_url']
        self.available_models = API_CONFIG['anthropic']['models']
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0
        self.rate_limit_remaining = 50  # Default conservative value
        self.rate_limit_reset = 0

        # Model-specific configurations
        self.model_configs = {
            'claude-2': {
                'max_tokens': 100000,
                'supports_system': True,
                'default_temperature': 0.7,
                'token_limit': 100000,
                'retry_limit': 3
            },
            'claude-instant': {
                'max_tokens': 100000,
                'supports_system': True,
                'default_temperature': 0.7,
                'token_limit': 100000,
                'retry_limit': 3
            }
        }

    async def _init_session(self):
        """Initialize aiohttp session if not exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "x-api-key": self.api_key_manager.get_api_key('anthropic'),
                    "anthropic-version": "2023-06-01"
                }
            )

    async def _close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _handle_rate_limits(self):
        """Handle rate limiting and throttling"""
        current_time = time.time()
        
        # If we're near the rate limit, wait until reset
        if self.rate_limit_remaining < 5 and current_time < self.rate_limit_reset:
            wait_time = self.rate_limit_reset - current_time + 1
            logger.warning(f"Rate limit approaching, waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)
            
        # Ensure minimum time between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < 0.1:  # Minimum 100ms between requests
            await asyncio.sleep(0.1 - time_since_last)
        
        self.last_request_time = current_time

    def _update_rate_limits(self, headers: Dict[str, str]):
        """Update rate limit tracking from response headers"""
        try:
            self.rate_limit_remaining = int(headers.get('x-ratelimit-remaining', 50))
            self.rate_limit_reset = time.time() + int(headers.get('x-ratelimit-reset', 60))
        except (ValueError, TypeError):
            logger.warning("Failed to parse rate limit headers")

    @handle_exceptions
    async def process_request(
        self,
        request_type: str,
        parameters: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process a request through Anthropic's API"""
        await self._init_session()
        await self._handle_rate_limits()
        
        start_time = time.time()
        model = parameters.get('model', 'claude-2')
        
        try:
            if request_type == 'text_generation':
                response = await self._generate_text(parameters, timeout)
            else:
                raise CustomException(
                    "API_007",
                    "Unsupported request type for Anthropic",
                    {"request_type": request_type}
                )

            latency = time.time() - start_time
            
            return {
                'success': True,
                'provider': 'anthropic',
                'model': model,
                'response': response,
                'latency': latency,
                'tokens': self._calculate_tokens(response),
                'timestamp': datetime.utcnow().timestamp()
            }

        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {str(e)}")
            raise CustomException(
                "API_002",
                "Rate limit exceeded",
                {"retry_after": e.headers.get('retry-after', 60)}
            )
            
        except APITimeoutError as e:
            logger.error(f"Request timeout: {str(e)}")
            raise CustomException(
                "API_008",
                "Request timeout",
                {"timeout": timeout}
            )
            
        except APIError as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise CustomException(
                "API_001",
                "API request failed",
                {"error": str(e)}
            )
            
        finally:
            if 'response' in locals():
                self._update_rate_limits(response.headers)

    async def _generate_text(
        self,
        parameters: Dict[str, Any],
        timeout: Optional[int]
    ) -> Dict[str, Any]:
        """Generate text using Claude models"""
        model = parameters.get('model', 'claude-2')
        
        # Format messages according to Anthropic's API
        messages = parameters.get('messages', [])
        if not messages:
            messages = [{"role": "user", "content": parameters.get('prompt', '')}]
            
        # Convert messages to Anthropic format
        formatted_messages = []
        system_message = None
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            else:
                formatted_messages.append({
                    'role': 'assistant' if msg['role'] == 'assistant' else 'user',
                    'content': msg['content']
                })
        
        request_data = {
            "model": model,
            "messages": formatted_messages,
            "max_tokens": min(
                parameters.get('max_tokens', self.model_configs[model]['max_tokens']),
                self.model_configs[model]['token_limit']
            ),
            "temperature": parameters.get('temperature', self.model_configs[model]['default_temperature']),
            "stream": False
        }
        
        if system_message and self.model_configs[model]['supports_system']:
            request_data['system'] = system_message

        async with self.session.post(
            f"{self.base_url}/messages",
            json=request_data,
            timeout=timeout
        ) as response:
            response.raise_for_status()
            return await response.json()

    def _calculate_tokens(self, response: Dict[str, Any]) -> Dict[str, int]:
        """Calculate token usage from response"""
        usage = response.get('usage', {})
        return {
            'prompt_tokens': usage.get('input_tokens', 0),
            'completion_tokens': usage.get('output_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }

    @handle_exceptions
    async def check_status(self) -> Dict[str, Any]:
        """Check API status and available models"""
        await self._init_session()
        
        try:
            # Anthropic doesn't have a dedicated status endpoint,
            # so we'll make a minimal request to check availability
            test_request = {
                "model": "claude-instant",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1
            }
            
            async with self.session.post(
                f"{self.base_url}/messages",
                json=test_request,
                timeout=10
            ) as response:
                response.raise_for_status()
                
                return {
                    'status': 'operational',
                    'available_models': self.available_models,
                    'rate_limit_remaining': self.rate_limit_remaining,
                    'rate_limit_reset': self.rate_limit_reset
                }
                
        except Exception as e:
            logger.error(f"Failed to check Anthropic API status: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().timestamp()
            }

    @handle_exceptions
    async def list_models(self) -> List[str]:
        """Get list of available models"""
        return self.available_models

    async def cleanup(self):
        """Cleanup resources"""
        await self._close_session()

    def __str__(self) -> str:
        return f"AnthropicAPI(models={len(self.available_models)})"

    def __repr__(self) -> str:
        return f"AnthropicAPI(base_url={self.base_url}, models={self.available_models})"
