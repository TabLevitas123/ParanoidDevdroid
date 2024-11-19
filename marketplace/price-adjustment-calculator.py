import random
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamicPriceAdjuster:
    """Class to handle dynamic price adjustments based on demand and supply."""
    def __init__(self, base_price: float, demand: int, supply: int):
        self.base_price = base_price
        self.demand = demand
        self.supply = supply

    def calculate_price(self) -> float:
        """Calculate the adjusted price based on demand and supply."""
        if self.supply == 0:
            logger.warning("Supply is zero. Returning maximum price.")
            return self.base_price * 2.0  # Arbitrary maximum price multiplier
        demand_supply_ratio = self.demand / self.supply
        adjusted_price = self.base_price * (1 + 0.1 * demand_supply_ratio)
        logger.info(f"Base Price: {self.base_price}, Demand: {self.demand}, Supply: {self.supply}, Adjusted Price: {adjusted_price}")
        return max(adjusted_price, 0.01)  # Ensure price doesn't fall below a minimal threshold

if __name__ == '__main__':
    # Example usage
    demand = random.randint(50, 150)
    supply = random.randint(10, 100)
    base_price = 10.0
    adjuster = DynamicPriceAdjuster(base_price, demand, supply)
    final_price = adjuster.calculate_price()
    print(f"Final adjusted price: {final_price}")
