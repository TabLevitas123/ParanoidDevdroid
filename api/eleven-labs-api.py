# services/api_integration/eleven_labs_api.py

import asyncio
from typing import Dict, List, Any, Optional
import time
from datetime import datetime
import aiohttp
import json

from elevenlabs import AsyncElevenLabs
from elevenlabs.api import Voices, Models, Voice, VoiceSettings
from elevenlabs.api.error import APIError, RateLimitError

from config.api_keys import APIKeyManager
from config.constants import API_CONFIG
from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions

logger = CustomLogger("eleven_labs_api", "elevenlabs_integration.log")

class ElevenLabsAPI:
    def __init__(self):
        self.api_key_manager = APIKeyManager()
        self.base_url = API_CONFIG['elevenlabs']['base_url']
        self.session: Optional[aiohttp.ClientSession] = None
        self.eleven_labs: Optional[AsyncElevenLabs] = None
        self.last_request_time = 0
        self.rate_limit_remaining = 50
        self.rate_limit_reset = 0
        
        # Voice and model configurations
        self.voice_configs = {}  # Will be populated during initialization
        self.model_configs = {
            'eleven_multilingual_v2': {
                'name': 'Eleven Multilingual v2',
                'supported_languages': ['en', 'de', 'pl', 'es', 'it', 'fr', 'pt', 'hi'],
                'max_text_length': 5000,
                'latency_optimization': True
            },
            'eleven_monolingual_v1': {
                'name': 'Eleven English v1',
                'supported_languages': ['en'],
                'max_text_length': 5000,
                'latency_optimization': False
            }
        }

    async def _init_session(self):
        """Initialize API sessions if not exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "xi-api-key": self.api_key_manager.get_api_key('elevenlabs'),
                    "Content-Type": "application/json"
                }
            )
            
        if self.eleven_labs is None:
            self.eleven_labs = AsyncElevenLabs(
                api_key=self.api_key_manager.get_api_key('elevenlabs')
            )
            
            # Fetch and cache available voices
            await self._refresh_voice_configs()

    async def _refresh_voice_configs(self):
        """Fetch and cache available voices"""
        try:
            voices = await self.eleven_labs.voices.get_all()
            self.voice_configs = {
                voice.name: {
                    'voice_id': voice.voice_id,
                    'category': voice.category,
                    'settings': voice.settings.dict(),
                    'labels': voice.labels
                }
                for voice in voices
            }
        except Exception as e:
            logger.error(f"Failed to fetch voice configs: {str(e)}")
            self.voice_configs = {}

    async def _close_session(self):
        """Close API sessions"""
        if self.session and not self.session.closed:
            await self.session.close()
        if self.eleven_labs:
            await self.eleven_labs.close()

    async def _handle_rate_limits(self):
        """Handle rate limiting and throttling"""
        current_time = time.time()
        
        if self.rate_limit_remaining < 5 and current_time < self.rate_limit_reset:
            wait_time = self.rate_limit_reset - current_time + 1
            logger.warning(f"Rate limit approaching, waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)
        
        time_since_last = current_time - self.last_request_time
        if time_since_last < 0.2:  # Minimum 200ms between requests
            await asyncio.sleep(0.2 - time_since_last)
        
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
        """Process a request through ElevenLabs API"""
        await self._init_session()
        await self._handle_rate_limits()
        
        start_time = time.time()
        model = parameters.get('model', 'eleven_multilingual_v2')
        
        try:
            if request_type == 'speech_synthesis':
                response = await self._generate_speech(parameters, timeout)
            else:
                raise CustomException(
                    "API_007",
                    "Unsupported request type for ElevenLabs",
                    {"request_type": request_type}
                )

            latency = time.time() - start_time
            
            return {
                'success': True,
                'provider': 'elevenlabs',
                'model': model,
                'response': response,
                'latency': latency,
                'timestamp': datetime.utcnow().timestamp()
            }

        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {str(e)}")
            raise CustomException(
                "API_002",
                "Rate limit exceeded",
                {"retry_after": 60}
            )
            
        except APIError as e:
            logger.error(f"ElevenLabs API error: {str(e)}")
            raise CustomException(
                "API_001",
                "API request failed",
                {"error": str(e)}
            )
            
        finally:
            if 'response' in locals():
                self._update_rate_limits(response.headers)

    async def _generate_speech(
        self,
        parameters: Dict[str, Any],
        timeout: Optional[int]
    ) -> Dict[str, Any]:
        """Generate speech using ElevenLabs TTS"""
        model = parameters.get('model', 'eleven_multilingual_v2')
        model_config = self.model_configs[model]
        
        # Validate text length
        text = parameters['text']
        if len(text) > model_config['max_text_length']:
            raise CustomException(
                "API_009",
                "Text exceeds maximum length",
                {
                    "max_length": model_config['max_text_length'],
                    "provided_length": len(text)
                }
            )
        
        # Get voice configuration
        voice_name = parameters.get('voice', 'Rachel')
        if voice_name not in self.voice_configs:
            raise CustomException(
                "API_010",
                "Invalid voice selected",
                {
                    "voice": voice_name,
                    "available_voices": list(self.voice_configs.keys())
                }
            )
        
        voice_config = self.voice_configs[voice_name]
        
        # Configure voice settings
        voice_settings = voice_config['settings'].copy()
        if 'stability' in parameters:
            voice_settings['stability'] = parameters['stability']
        if 'similarity_boost' in parameters:
            voice_settings['similarity_boost'] = parameters['similarity_boost']
        if 'style' in parameters:
            voice_settings['style'] = parameters['style']
        if 'use_speaker_boost' in parameters:
            voice_settings['use_speaker_boost'] = parameters['use_speaker_boost']
        
        try:
            # Generate audio
            audio_stream = await self.eleven_labs.generate(
                text=text,
                voice_id=voice_config['voice_id'],
                model_id=model,
                voice_settings=voice_settings,
                optimization=model_config['latency_optimization']
            )
            
            # Convert audio stream to bytes
            audio_data = await audio_stream.read()
            
            return {
                'audio': audio_data,
                'meta': {
                    'model': model,
                    'voice': voice_name,
                    'text_length': len(text),
                    'settings': voice_settings
                }
            }
            
        except Exception as e:
            logger.error(f"Speech generation failed: {str(e)}")
            raise CustomException(
                "API_011",
                "Speech generation failed",
                {"error": str(e)}
            )

    @handle_exceptions
    async def check_status(self) -> Dict[str, Any]:
        """Check API status and available voices"""
        await self._init_session()
        
        try:
            # Refresh voice configurations
            await self._refresh_voice_configs()
            
            # Check subscription status
            async with self.session.get(
                f"{self.base_url}/user/subscription",
                timeout=10
            ) as response:
                response.raise_for_status()
                subscription = await response.json()
                
                return {
                    'status': 'operational',
                    'available_voices': list(self.voice_configs.keys()),
                    'available_models': list(self.model_configs.keys()),
                    'subscription': {
                        'tier': subscription.get('tier'),
                        'character_count': subscription.get('character_count'),
                        'character_limit': subscription.get('character_limit')
                    },
                    'rate_limit_remaining': self.rate_limit_remaining,
                    'rate_limit_reset': self.rate_limit_reset
                }
                
        except Exception as e:
            logger.error(f"Failed to check ElevenLabs API status: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().timestamp()
            }

    @handle_exceptions
    async def list_models(self) -> List[str]:
        """Get list of available models"""
        return list(self.model_configs.keys())

    @handle_exceptions
    async def list_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices with their configurations"""
        await self._init_session()
        return [
            {
                'name': name,
                'category': config['category'],
                'labels': config['labels']
            }
            for name, config in self.voice_configs.items()
        ]

    async def cleanup(self):
        """Cleanup resources"""
        await self._close_session()

    def __str__(self) -> str:
        return f"ElevenLabsAPI(voices={len(self.voice_configs)})"

    def __repr__(self) -> str:
        return f"ElevenLabsAPI(base_url={self.base_url}, models={list(self.model_configs.keys())})"
