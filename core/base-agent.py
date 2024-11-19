# agents/base_agent.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import uuid
from queue import PriorityQueue

from config.constants import AgentStatus
from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions

logger = CustomLogger("base_agent", "agents.log")

class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Base Agent",
        description: str = "",
        owner_id: Optional[str] = None,
        capabilities: Optional[List[str]] = None
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.owner_id = owner_id
        self.capabilities = capabilities or []
        self.status = AgentStatus.INACTIVE
        self.created_at = datetime.utcnow()
        self.last_active = None
        self.task_queue = PriorityQueue()
        self.execution_history = []
        self.wallet_address = None
        self.performance_metrics = {
            "tasks_completed": 0,
            "success_rate": 0.0,
            "average_response_time": 0.0,
            "total_tokens_spent": 0
        }

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the agent and its required resources"""
        pass

    @abstractmethod
    async def perform_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task"""
        pass

    @handle_exceptions
    async def add_task(self, task: Dict[str, Any], priority: int = 1) -> bool:
        """Add a task to the agent's queue"""
        try:
            if not self._validate_task(task):
                raise CustomException(
                    "AGENT_003",
                    "Invalid task format",
                    {"task": task}
                )

            task_entry = {
                "id": str(uuid.uuid4()),
                "priority": priority,
                "timestamp": datetime.utcnow(),
                "status": "pending",
                "data": task
            }
            
            self.task_queue.put((priority, task_entry))
            logger.info(f"Task {task_entry['id']} added to queue for agent {self.agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add task: {str(e)}")
            raise

    @handle_exceptions
    async def process_queue(self) -> None:
        """Process tasks in the queue"""
        while not self.task_queue.empty():
            try:
                _, task_entry = self.task_queue.get()
                task_entry["status"] = "processing"
                
                start_time = datetime.utcnow()
                result = await self.perform_task(task_entry["data"])
                end_time = datetime.utcnow()
                
                # Update performance metrics
                self._update_metrics(start_time, end_time, result)
                
                # Log execution history
                self._log_execution(task_entry, result, start_time, end_time)
                
                self.last_active = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Error processing task: {str(e)}")
                task_entry["status"] = "failed"
                self._log_execution(
                    task_entry,
                    {"error": str(e)},
                    start_time,
                    datetime.utcnow()
                )

    def _validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate task format and requirements"""
        required_fields = ["type", "parameters"]
        return all(field in task for field in required_fields)

    def _update_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        result: Dict[str, Any]
    ) -> None:
        """Update agent performance metrics"""
        execution_time = (end_time - start_time).total_seconds()
        self.performance_metrics["tasks_completed"] += 1
        
        # Update success rate
        success = result.get("success", False)
        total_tasks = self.performance_metrics["tasks_completed"]
        current_success_rate = self.performance_metrics["success_rate"]
        new_success_rate = ((current_success_rate * (total_tasks - 1)) + (1 if success else 0)) / total_tasks
        self.performance_metrics["success_rate"] = new_success_rate
        
        # Update average response time
        current_avg_time = self.performance_metrics["average_response_time"]
        new_avg_time = ((current_avg_time * (total_tasks - 1)) + execution_time) / total_tasks
        self.performance_metrics["average_response_time"] = new_avg_time
        
        # Update token usage if provided in result
        if "tokens_used" in result:
            self.performance_metrics["total_tokens_spent"] += result["tokens_used"]

    def _log_execution(
        self,
        task_entry: Dict[str, Any],
        result: Dict[str, Any],
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """Log task execution details"""
        execution_record = {
            "task_id": task_entry["id"],
            "task_type": task_entry["data"]["type"],
            "start_time": start_time,
            "end_time": end_time,
            "duration": (end_time - start_time).total_seconds(),
            "status": "completed" if result.get("success", False) else "failed",
            "result": result
        }
        self.execution_history.append(execution_record)

    @handle_exceptions
    async def update_status(self, new_status: AgentStatus) -> bool:
        """Update agent status"""
        if new_status not in AgentStatus:
            raise CustomException(
                "AGENT_004",
                "Invalid agent status",
                {"status": new_status}
            )
            
        self.status = new_status
        logger.info(f"Agent {self.agent_id} status updated to {new_status.value}")
        return True

    @property
    def is_available(self) -> bool:
        """Check if agent is available to process tasks"""
        return (
            self.status == AgentStatus.ACTIVE and
            self.task_queue.qsize() < 100  # Configurable maximum queue size
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "metrics": self.performance_metrics,
            "queue_size": self.task_queue.qsize(),
            "last_active": self.last_active
        }

    async def cleanup(self) -> None:
        """Cleanup agent resources"""
        # Implement cleanup logic in derived classes
        pass

    def __str__(self) -> str:
        return f"{self.name} (ID: {self.agent_id}, Status: {self.status.value})"

    def __repr__(self) -> str:
        return f"BaseAgent(id={self.agent_id}, name={self.name}, status={self.status.value})"
