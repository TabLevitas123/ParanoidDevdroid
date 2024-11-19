# services/pricing/base_price_calculator.py

from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
import json

from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions

logger = CustomLogger("base_price_calculator", "pricing.log")

class BasePriceCalculator:
    """Handles base price calculations for different AI services"""
    
    def __init__(self):
        # Base prices per unit (token, second, image)
        self.base_rates = {
            'text_generation': {
                'gpt-4': Decimal('0.0001'),  # per token
                'gpt-3.5-turbo': Decimal('0.00002'),
                'claude-2': Decimal('0.00008'),
                'claude-instant': Decimal('0.00004')
            },
            'image_generation': {
                'stable-diffusion-xl': Decimal('0.02'),  # per image
                'stable-diffusion-v1-5': Decimal('0.01')
            },
            'speech_synthesis': {
                'eleven_multilingual_v2': Decimal('0.0003'),  # per character
                'eleven_monolingual_v1': Decimal('0.0002')
            }
        }
        
        # Quality multipliers
        self.quality_multipliers = {
            'high': Decimal('1.5'),
            'medium': Decimal('1.0'),
            'low': Decimal('0.8')
        }
        
        # Size multipliers for image generation
        self.size_multipliers = {
            '256x256': Decimal('0.8'),
            '512x512': Decimal('1.0'),
            '1024x1024': Decimal('1.5')
        }

    @handle_exceptions
    async def calculate_text_price(
        self,
        model: str,
        token_count: int,
        quality: str = 'medium'
    ) -> Decimal:
        """Calculate price for text generation"""
        if model not in self.base_rates['text_generation']:
            raise CustomException(
                "PRICE_001",
                "Invalid model specified",
                {"model": model, "valid_models": list(self.base_rates['text_generation'].keys())}
            )
            
        if quality not in self.quality_multipliers:
            raise CustomException(
                "PRICE_002",
                "Invalid quality level",
                {"quality": quality, "valid_levels": list(self.quality_multipliers.keys())}
            )
            
        base_rate = self.base_rates['text_generation'][model]
        quality_multiplier = self.quality_multipliers[quality]
        
        return base_rate * Decimal(str(token_count)) * quality_multiplier

    @handle_exceptions
    async def calculate_image_price(
        self,
        model: str,
        size: str,
        quantity: int = 1,
        quality: str = 'medium'
    ) -> Decimal:
        """Calculate price for image generation"""
        if model not in self.base_rates['image_generation']:
            raise CustomException(
                "PRICE_001",
                "Invalid model specified",
                {"model": model, "valid_models": list(self.base_rates['image_generation'].keys())}
            )
            
        if size not in self.size_multipliers:
            raise CustomException(
                "PRICE_003",
                "Invalid image size",
                {"size": size, "valid_sizes": list(self.size_multipliers.keys())}
            )
            
        if quality not in self.quality_multipliers:
            raise CustomException(
                "PRICE_002",
                "Invalid quality level",
                {"quality": quality, "valid_levels": list(self.quality_multipliers.keys())}
            )
            
        base_rate = self.base_rates['image_generation'][model]
        size_multiplier = self.size_multipliers[size]
        quality_multiplier = self.quality_multipliers[quality]
        
        return base_rate * size_multiplier * quality_multiplier * Decimal(str(quantity))

    @handle_exceptions
    async def calculate_speech_price(
        self,
        model: str,
        character_count: int,
        quality: str = 'medium'
    ) -> Decimal:
        """Calculate price for speech synthesis"""
        if model not in self.base_rates['speech_synthesis']:
            raise CustomException(
                "PRICE_001",
                "Invalid model specified",
                {"model": model, "valid_models": list(self.base_rates['speech_synthesis'].keys())}
            )
            
        if quality not in self.quality_multipliers:
            raise CustomException(
                "PRICE_002",
                "Invalid quality level",
                {"quality": quality, "valid_levels": list(self.quality_multipliers.keys())}
            )
            
        base_rate = self.base_rates['speech_synthesis'][model]
        quality_multiplier = self.quality_multipliers[quality]
        
        return base_rate * Decimal(str(character_count)) * quality_multiplier

    @handle_exceptions
    async def update_base_rate(
        self,
        service_type: str,
        model: str,
        new_rate: Decimal
    ) -> bool:
        """Update base rate for a specific model"""
        if service_type not in self.base_rates:
            raise CustomException(
                "PRICE_004",
                "Invalid service type",
                {"service_type": service_type, "valid_types": list(self.base_rates.keys())}
            )
            
        if model not in self.base_rates[service_type]:
            raise CustomException(
                "PRICE_001",
                "Invalid model specified",
                {"model": model, "valid_models": list(self.base_rates[service_type].keys())}
            )
            
        if new_rate <= 0:
            raise CustomException(
                "PRICE_005",
                "Invalid rate value",
                {"rate": new_rate}
            )
            
        self.base_rates[service_type][model] = new_rate
        logger.info(f"Updated base rate for {model} to {new_rate}")
        return True

    @handle_exceptions
    async def update_multiplier(
        self,
        multiplier_type: str,
        key: str,
        value: Decimal
    ) -> bool:
        """Update quality or size multiplier"""
        if multiplier_type == 'quality':
            if key not in self.quality_multipliers:
                raise CustomException(
                    "PRICE_002",
                    "Invalid quality level",
                    {"quality": key, "valid_levels": list(self.quality_multipliers.keys())}
                )
            self.quality_multipliers[key] = value
            
        elif multiplier_type == 'size':
            if key not in self.size_multipliers:
                raise CustomException(
                    "PRICE_003",
                    "Invalid image size",
                    {"size": key, "valid_sizes": list(self.size_multipliers.keys())}
                )
            self.size_multipliers[key] = value
            
        else:
            raise CustomException(
                "PRICE_006",
                "Invalid multiplier type",
                {"type": multiplier_type, "valid_types": ['quality', 'size']}
            )
            
        logger.info(f"Updated {multiplier_type} multiplier for {key} to {value}")
        return True

    async def get_price_structure(self) -> Dict[str, Any]:
        """Get current price structure"""
        return {
            'base_rates': {
                service: {
                    model: float(rate)
                    for model, rate in models.items()
                }
                for service, models in self.base_rates.items()
            },
            'quality_multipliers': {
                quality: float(multiplier)
                for quality, multiplier in self.quality_multipliers.items()
            },
            'size_multipliers': {
                size: float(multiplier)
                for size, multiplier in self.size_multipliers.items()
            }
        }

    def __str__(self) -> str:
        return "BasePriceCalculator"

    def __repr__(self) -> str:
        return f"BasePriceCalculator(services={list(self.base_rates.keys())})"
