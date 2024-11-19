import random
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoadBalancer:
    """Class for managing and balancing load across servers."""
    def __init__(self, servers: List[str]):
        self.servers = servers
        self.server_loads = {server: 0 for server in servers}
        logger.info("Load Balancer initialized.")

    def route_request(self) -> str:
        """Route a request to the server with the least load."""
        target_server = min(self.server_loads, key=self.server_loads.get)
        self.server_loads[target_server] += 1
        logger.info(f"Request routed to server: {target_server}")
        return target_server

    def release_load(self, server: str):
        """Release load from a specific server."""
        if server in self.server_loads and self.server_loads[server] > 0:
            self.server_loads[server] -= 1
            logger.info(f"Load released from server: {server}")

if __name__ == '__main__':
    servers = ["server1", "server2", "server3"]
    balancer = LoadBalancer(servers)
    for _ in range(5):
        server = balancer.route_request()
        print(f"Request routed to: {server}")
    balancer.release_load("server1")
    print("Server Loads:", balancer.server_loads)
