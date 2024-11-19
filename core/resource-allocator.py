import threading
import logging
from typing import Any, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResourceAllocator:
    """Class for managing and allocating resources."""
    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._lock = threading.Lock()
        logger.info("Resource Allocator initialized.")

    def add_resource(self, resource_name: str, resource: Any):
        """Add a resource to the allocator."""
        with self._lock:
            if resource_name in self._resources:
                logger.warning(f"Resource {resource_name} already exists.")
                return
            self._resources[resource_name] = resource
            logger.info(f"Resource {resource_name} added.")

    def allocate_resource(self, resource_name: str) -> Any:
        """Allocate a resource by its name."""
        with self._lock:
            resource = self._resources.get(resource_name)
            if not resource:
                logger.warning(f"Resource {resource_name} not found.")
                return None
            logger.info(f"Resource {resource_name} allocated.")
            return resource

if __name__ == '__main__':
    allocator = ResourceAllocator()
    allocator.add_resource("db_connection", "Database Connection Object")
    resource = allocator.allocate_resource("db_connection")
    print("Allocated Resource:", resource)
