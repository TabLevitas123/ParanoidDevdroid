# marketplace/marketplace_core.py

from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from decimal import Decimal

from config.constants import TransactionStatus
from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions
from utils.validation_utils import Validator
from tokens.token_manager import TokenManager
from agents.agent_manager import AgentManager

logger = CustomLogger("marketplace", "marketplace.log")

class MarketplaceCore:
    def __init__(
        self,
        token_manager: TokenManager,
        agent_manager: AgentManager,
        marketplace_fee: float = 0.025  # 2.5% fee
    ):
        self.token_manager = token_manager
        self.agent_manager = agent_manager
        self.marketplace_fee = Decimal(str(marketplace_fee))
        self.listings: Dict[str, Dict[str, Any]] = {}
        self.transactions: Dict[str, Dict[str, Any]] = {}
        self.validator = Validator()

    @handle_exceptions
    async def create_listing(
        self,
        agent_id: str,
        seller_id: str,
        price: float,
        description: str = "",
        tags: Optional[List[str]] = None,
        duration_days: int = 30
    ) -> str:
        """Create a new marketplace listing for an agent"""
        # Validate agent ownership
        agent = await self.agent_manager.get_agent(agent_id)
        if agent.owner_id != seller_id:
            raise CustomException(
                "MARKET_003",
                "Unauthorized listing attempt",
                {"agent_id": agent_id, "seller_id": seller_id}
            )

        # Validate price
        if not self.validator.validate_token_amount(price, min_amount=0.000001):
            raise CustomException(
                "MARKET_004",
                "Invalid listing price",
                {"price": price}
            )

        listing_id = str(uuid.uuid4())
        expiration_date = datetime.utcnow().timestamp() + (duration_days * 86400)

        listing = {
            "listing_id": listing_id,
            "agent_id": agent_id,
            "seller_id": seller_id,
            "price": Decimal(str(price)),
            "description": description,
            "tags": tags or [],
            "created_at": datetime.utcnow().timestamp(),
            "expires_at": expiration_date,
            "status": "active",
            "views": 0,
            "favorites": set(),
            "transaction_history": []
        }

        self.listings[listing_id] = listing
        logger.info(f"Created listing {listing_id} for agent {agent_id}")
        return listing_id

    @handle_exceptions
    async def purchase_agent(
        self,
        listing_id: str,
        buyer_id: str
    ) -> Dict[str, Any]:
        """Process agent purchase transaction"""
        if listing_id not in self.listings:
            raise CustomException(
                "MARKET_005",
                "Listing not found",
                {"listing_id": listing_id}
            )

        listing = self.listings[listing_id]
        if listing["status"] != "active":
            raise CustomException(
                "MARKET_006",
                "Listing is not active",
                {"listing_id": listing_id, "status": listing["status"]}
            )

        if listing["seller_id"] == buyer_id:
            raise CustomException(
                "MARKET_007",
                "Cannot purchase your own listing",
                {"listing_id": listing_id}
            )

        # Calculate fees and total price
        base_price = listing["price"]
        marketplace_fee_amount = base_price * self.marketplace_fee
        total_price = base_price + marketplace_fee_amount

        # Check buyer's balance
        if not await self.token_manager.check_balance(buyer_id, float(total_price)):
            raise CustomException(
                "MARKET_008",
                "Insufficient balance",
                {
                    "required": float(total_price),
                    "marketplace_fee": float(marketplace_fee_amount)
                }
            )

        # Create transaction record
        transaction_id = str(uuid.uuid4())
        transaction = {
            "transaction_id": transaction_id,
            "listing_id": listing_id,
            "agent_id": listing["agent_id"],
            "seller_id": listing["seller_id"],
            "buyer_id": buyer_id,
            "base_price": base_price,
            "marketplace_fee": marketplace_fee_amount,
            "total_price": total_price,
            "status": TransactionStatus.PENDING,
            "created_at": datetime.utcnow().timestamp(),
            "completed_at": None
        }

        try:
            # Process payments
            await self.token_manager.transfer(
                from_address=buyer_id,
                to_address=listing["seller_id"],
                amount=float(base_price)
            )

            await self.token_manager.transfer(
                from_address=buyer_id,
                to_address="marketplace_treasury",  # Treasury wallet address
                amount=float(marketplace_fee_amount)
            )

            # Transfer agent ownership
            agent = await self.agent_manager.get_agent(listing["agent_id"])
            original_owner = agent.owner_id
            agent.owner_id = buyer_id

            # Update agent in manager
            self.agent_manager.owner_agents[original_owner].remove(agent.agent_id)
            self.agent_manager.owner_agents[buyer_id].append(agent.agent_id)

            # Update transaction status
            transaction["status"] = TransactionStatus.COMPLETED
            transaction["completed_at"] = datetime.utcnow().timestamp()

            # Update listing
            listing["status"] = "sold"
            listing["transaction_history"].append(transaction_id)

            # Store transaction
            self.transactions[transaction_id] = transaction

            logger.info(f"Completed transaction {transaction_id} for listing {listing_id}")
            return {
                "success": True,
                "transaction_id": transaction_id,
                "transaction": transaction
            }

        except Exception as e:
            transaction["status"] = TransactionStatus.FAILED
            self.transactions[transaction_id] = transaction
            logger.error(f"Transaction failed: {str(e)}")
            raise CustomException(
                "MARKET_009",
                "Transaction failed",
                {"error": str(e)}
            )

    @handle_exceptions
    async def get_listing(self, listing_id: str) -> Dict[str, Any]:
        """Retrieve listing details"""
        if listing_id not in self.listings:
            raise CustomException(
                "MARKET_005",
                "Listing not found",
                {"listing_id": listing_id}
            )

        listing = self.listings[listing_id].copy()
        listing["favorites"] = len(listing["favorites"])  # Convert set to count
        return listing

    @handle_exceptions
    async def search_listings(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search marketplace listings with filters"""
        results = []
        
        for listing in self.listings.values():
            if listing["status"] != "active":
                continue

            # Apply filters
            if query and query.lower() not in listing["description"].lower():
                continue

            if tags and not all(tag in listing["tags"] for tag in tags):
                continue

            if min_price and listing["price"] < Decimal(str(min_price)):
                continue

            if max_price and listing["price"] > Decimal(str(max_price)):
                continue

            # Add to results
            listing_copy = listing.copy()
            listing_copy["favorites"] = len(listing_copy["favorites"])
            results.append(listing_copy)

        # Sort results
        reverse = sort_order.lower() == "desc"
        results.sort(key=lambda x: x[sort_by], reverse=reverse)

        # Apply pagination
        return results[offset:offset + limit]

    @handle_exceptions
    async def update_listing(
        self,
        listing_id: str,
        seller_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update listing details"""
        if listing_id not in self.listings:
            raise CustomException(
                "MARKET_005",
                "Listing not found",
                {"listing_id": listing_id}
            )

        listing = self.listings[listing_id]
        if listing["seller_id"] != seller_id:
            raise CustomException(
                "MARKET_003",
                "Unauthorized update attempt",
                {"listing_id": listing_id, "seller_id": seller_id}
            )

        allowed_updates = {"description", "tags", "price"}
        invalid_fields = set(updates.keys()) - allowed_updates
        if invalid_fields:
            raise CustomException(
                "MARKET_010",
                "Invalid update fields",
                {"invalid_fields": list(invalid_fields)}
            )

        if "price" in updates:
            if not self.validator.validate_token_amount(updates["price"], min_amount=0.000001):
                raise CustomException(
                    "MARKET_004",
                    "Invalid listing price",
                    {"price": updates["price"]}
                )
            updates["price"] = Decimal(str(updates["price"]))

        # Apply updates
        listing.update({k: v for k, v in updates.items() if k in allowed_updates})
        logger.info(f"Updated listing {listing_id}")
        return True

    @handle_exceptions
    async def toggle_favorite(
        self,
        listing_id: str,
        user_id: str
    ) -> bool:
        """Toggle favorite status for a listing"""
        if listing_id not in self.listings:
            raise CustomException(
                "MARKET_005",
                "Listing not found",
                {"listing_id": listing_id}
            )

        listing = self.listings[listing_id]
        if user_id in listing["favorites"]:
            listing["favorites"].remove(user_id)
            action = "removed from"
        else:
            listing["favorites"].add(user_id)
            action = "added to"

        logger.info(f"User {user_id} {action} favorites for listing {listing_id}")
        return True

    @handle_exceptions
    async def get_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Retrieve transaction details"""
        if transaction_id not in self.transactions:
            raise CustomException(
                "MARKET_011",
                "Transaction not found",
                {"transaction_id": transaction_id}
            )

        transaction = self.transactions[transaction_id]
        if user_id not in [transaction["buyer_id"], transaction["seller_id"]]:
            raise CustomException(
                "MARKET_012",
                "Unauthorized transaction access",
                {"transaction_id": transaction_id}
            )

        return transaction

    async def cleanup_expired_listings(self) -> None:
        """Remove expired listings"""
        current_time = datetime.utcnow().timestamp()
        expired_listings = [
            listing_id for listing_id, listing in self.listings.items()
            if listing["status"] == "active" and listing["expires_at"] < current_time
        ]

        for listing_id in expired_listings:
            self.listings[listing_id]["status"] = "expired"
            logger.info(f"Expired listing {listing_id}")

    def __str__(self) -> str:
        active_listings = sum(1 for l in self.listings.values() if l["status"] == "active")
        return f"MarketplaceCore(active_listings={active_listings})"

    def __repr__(self) -> str:
        return f"MarketplaceCore(listings={len(self.listings)}, transactions={len(self.transactions)})"
