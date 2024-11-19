import threading
import logging
from typing import List, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Agent:
    """Class representing an individual agent."""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.running = False

    def start(self):
        """Start the agent's operations."""
        if self.running:
            logger.warning(f"Agent {self.agent_id} is already running.")
            return
        self.running = True
        logger.info(f"Agent {self.agent_id} started.")

    def stop(self):
        """Stop the agent's operations."""
        if not self.running:
            logger.warning(f"Agent {self.agent_id} is not running.")
            return
        self.running = False
        logger.info(f"Agent {self.agent_id} stopped.")

class AgentManager:
    """Class for managing multiple agents."""
    def __init__(self):
        self.agents: Dict[str, Agent] = {}

    def add_agent(self, agent_id: str):
        """Add a new agent to the manager."""
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already exists.")
            return
        self.agents[agent_id] = Agent(agent_id)
        logger.info(f"Agent {agent_id} added.")

    def start_all_agents(self):
        """Start all agents managed by the agent manager."""
        for agent in self.agents.values():
            agent.start()

    def stop_all_agents(self):
        """Stop all agents managed by the agent manager."""
        for agent in self.agents.values():
            agent.stop()

if __name__ == '__main__':
    manager = AgentManager()
    manager.add_agent("agent_1")
    manager.add_agent("agent_2")
    manager.start_all_agents()
    manager.stop_all_agents()
