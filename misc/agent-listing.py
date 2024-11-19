# marketplace/agent_listing.py

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from decimal import Decimal

from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions
from utils.validation_utils import Validator

logger = CustomLogger("agent_listing", "marketplace.log")

class ListingState:
    """Enumeration of possible listing states"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    SOLD = "sold"
    EXPIRED = "expired"
    DELETED = "deleted"

class AgentListing:
    """Manages marketplace listings for agents"""
    def __init__(self, validator: Validator):
        self.validator = validator
        self.listings: Dict[str, Dict[str, Any]] = {}
        self.user_listings: Dict[str, List[str]] = {}  # user_id -> listing_ids
        self.category_listings: Dict[str, List[str]] = {}  # category -> listing_ids
        self.search_index: Dict[str, List[str]] = {}  # term -> listing_ids
        
        # Activity tracking
        self.views: Dict[str, int] = {}  # listing_id -> view_count
        self.favorites: Dict[str, set] = {}  # listing_id -> user_ids
        
        # Performance metrics
        self.metrics = {
            'total_listings': 0,
            'active_listings': 0,
            'total_views': 0,
            'total_favorites': 0,
            'average_price': Decimal('0'),
            'total_sales': 0
        }

    def _update_search_index(self, listing_id: str, listing_data: Dict[str, Any]) -> None:
        """Update search index with listing terms"""
        # Extract searchable terms
        terms = set()
        
        # Add name terms
        name_terms = listing_data['name'].lower().split()
        terms.update(name_terms)
        
        # Add description terms
        desc_terms = listing_data['description'].lower().split()
        terms.update(desc_terms)
        
        # Add categories and tags
        terms.update(listing_data['categories'])
        terms.update(listing_data['tags'])
        
        # Update index
        for term in terms:
            if term not in self.search_index:
                self.search_index[term] = []
            self.search_index[term].append(listing_id)

    @handle_exceptions
    async def create_listing(
        self,
        agent_id: str,
        user_id: str,
        name: str,
        description: str,
        price: Decimal,
        categories: List[str],
        tags: List[str],
        duration_days: int = 30
    ) -> str:
        """Create a new agent listing"""
        # Validate inputs
        if not name or len(name) > 100:
            raise CustomException(
                "LISTING_001",
                "Invalid listing name",
                {"max_length": 100}
            )
            
        if not description or len(description) > 5000:
            raise CustomException(
                "LISTING_002",
                "Invalid listing description",
                {"max_length": 5000}
            )
            
        if not self.validator.validate_token_amount(float(price)):
            raise CustomException(
                "LISTING_003",
                "Invalid listing price"
            )
            
        if not categories or len(categories) > 5:
            raise CustomException(
                "LISTING_004",
                "Invalid categories",
                {"max_categories": 5}
            )
            
        if len(tags) > 10:
            raise CustomException(
                "LISTING_005",
                "Too many tags",
                {"max_tags": 10}
            )
            
        # Create listing
        listing_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        expires_at = created_at.timestamp() + (duration_days * 86400)
        
        listing_data = {
            'listing_id': listing_id,
            'agent_id': agent_id,
            'user_id': user_id,
            'name': name,
            'description': description,
            'price': price,
            'categories': categories,
            'tags': tags,
            'state': ListingState.ACTIVE,
            'created_at': created_at.timestamp(),
            'expires_at': expires_at,
            'views': 0,
            'favorites_count': 0
        }
        
        # Store listing
        self.listings[listing_id] = listing_data
        
        # Update indices
        if user_id not in self.user_listings:
            self.user_listings[user_id] = []
        self.user_listings[user_id].append(listing_id)
        
        for category in categories:
            if category not in self.category_listings:
                self.category_listings[category] = []
            self.category_listings[category].append(listing_id)
            
        self._update_search_index(listing_id, listing_data)
        
        # Initialize tracking
        self.views[listing_id] = 0
        self.favorites[listing_id] = set()
        
        # Update metrics
        self.metrics['total_listings'] += 1
        self.metrics['active_listings'] += 1
        self._update_price_metrics(price)
        
        logger.info(f"Created listing {listing_id} for agent {agent_id}")
        return listing_id

    def _update_price_metrics(self, price: Decimal) -> None:
        """Update price-related metrics"""
        total_listings = self.metrics['total_listings']
        current_avg = self.metrics['average_price']
        
        if total_listings == 1:
            self.metrics['average_price'] = price
        else:
            self.metrics['average_price'] = (
                (current_avg * (total_listings - 1) + price) / total_listings
            )

    @handle_exceptions
    async def update_listing(
        self,
        listing_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update an existing listing"""
        if listing_id not in self.listings:
            raise CustomException(
                "LISTING_006",
                "Listing not found"
            )
            
        listing = self.listings[listing_id]
        
        if listing['user_id'] != user_id:
            raise CustomException(
                "LISTING_007",
                "Unauthorized listing update"
            )
            
        if listing['state'] not in [ListingState.DRAFT, ListingState.ACTIVE, ListingState.PAUSED]:
            raise CustomException(
                "LISTING_008",
                "Cannot update listing in current state"
            )
            
        # Validate updates
        allowed_updates = {
            'name', 'description', 'price', 'categories', 'tags', 'state'
        }
        
        invalid_fields = set(updates.keys()) - allowed_updates
        if invalid_fields:
            raise CustomException(
                "LISTING_009",
                "Invalid update fields",
                {"invalid_fields": list(invalid_fields)}
            )
            
        # Apply updates
        old_data = listing.copy()
        listing.update(updates)
        
        # Update indices if necessary
        if 'categories' in updates:
            for category in old_data['categories']:
                self.category_listings[category].remove(listing_id)
            for category in updates['categories']:
                if category not in self.category_listings:
                    self.category_listings[category] = []
                self.category_listings[category].append(listing_id)
                
        if any(field in updates for field in ['name', 'description', 'categories', 'tags']):
            self._update_search_index(listing_id, listing)
            
        logger.info(f"Updated listing {listing_id}")
        return True

    @handle_exceptions
    async def get_listing(
        self,
        listing_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get listing details"""
        if listing_id not in self.listings:
            raise CustomException(
                "LISTING_006",
                "Listing not found"
            )
            
        listing = self.listings[listing_id].copy()
        
        # Increment view count if not owner
        if user_id and user_id != listing['user_id']:
            self.views[listing_id] += 1
            self.metrics['total_views'] += 1
            listing['views'] = self.views[listing_id]
            
        # Add favorite status
        listing['favorited'] = user_id in self.favorites[listing_id] if user_id else False
        
        return listing

    @handle_exceptions
    async def search_listings(
        self,
        query: Optional[str] = None,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        sort_by: str = 'created_at',
        sort_order: str = 'desc',
        offset: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search listings with filters"""
        # Get initial listing set
        listing_ids = set()
        
        if query:
            terms = query.lower().split()
            for term in terms:
                if term in self.search_index:
                    if not listing_ids:
                        listing_ids = set(self.search_index[term])
                    else:
                        listing_ids &= set(self.search_index[term])
        else:
            listing_ids = set(self.listings.keys())
            
        # Apply category filter
        if categories:
            category_listings = set()
            for category in categories:
                category_listings.update(self.category_listings.get(category, []))
            listing_ids &= category_listings
            
        # Apply tag filter
        if tags:
            listing_ids = {
                lid for lid in listing_ids
                if any(tag in self.listings[lid]['tags'] for tag in tags)
            }
            
        # Apply price filter
        if min_price is not None:
            listing_ids = {
                lid for lid in listing_ids
                if self.listings[lid]['price'] >= min_price
            }
            
        if max_price is not None:
            listing_ids = {
                lid for lid in listing_ids
                if self.listings[lid]['price'] <= max_price
            }
            
        # Sort results
        sorted_listings = sorted(
            [self.listings[lid] for lid in listing_ids],
            key=lambda x: x[sort_by],
            reverse=(sort_order == 'desc')
        )
        
        # Apply pagination
        return sorted_listings[offset:offset + limit]

    @handle_exceptions
    async def toggle_favorite(
        self,
        listing_id: str,
        user_id: str
    ) -> bool:
        """Toggle favorite status for a listing"""
        if listing_id not in self.listings:
            raise CustomException(
                "LISTING_006",
                "Listing not found"
            )
            
        if user_id in self.favorites[listing_id]:
            self.favorites[listing_id].remove(user_id)
            self.metrics['total_favorites'] -= 1
        else:
            self.favorites[listing_id].add(user_id)
            self.metrics['total_favorites'] += 1
            
        self.listings[listing_id]['favorites_count'] = len(self.favorites[listing_id])
        return True

    @handle_exceptions
    async def mark_as_sold(
        self,
        listing_id: str,
        user_id: str
    ) -> bool:
        """Mark listing as sold"""
        if listing_id not in self.listings:
            raise CustomException(
                "LISTING_006",
                "Listing not found"
            )
            
        listing = self.listings[listing_id]
        
        if listing['user_id'] != user_id:
            raise CustomException(
                "LISTING_007",
                "Unauthorized listing update"
            )
            
        listing['state'] = ListingState.SOLD
        self.metrics['total_sales'] += 1
        self.metrics['active_listings'] -= 1
        
        return True

    async def cleanup_expired_listings(self) -> None:
        """Mark expired listings"""
        current_time = datetime.utcnow().timestamp()
        
        for listing_id, listing in self.listings.items():
            if (listing['state'] == ListingState.ACTIVE and
                listing['expires_at'] < current_time):
                listing['state'] = ListingState.EXPIRED
                self.metrics['active_listings'] -= 1
                logger.info(f"Marked listing {listing_id} as expired")

    def __str__(self) -> str:
        return f"AgentListing(active={self.metrics['active_listings']})"

    def __repr__(self) -> str:
        return (f"AgentListing(total={self.metrics['total_listings']}, "
                f"active={self.metrics['active_listings']}, "
                f"sales={self.metrics['total_sales']})")
