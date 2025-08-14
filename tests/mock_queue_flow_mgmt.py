from random import randint
from mcp.server.fastmcp import FastMCP
import sys
from typing import Dict, TypedDict, Optional
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("mock_queuflow_mgmt", host="localhost", port=6969)

class PolicyConfig(TypedDict):
    arrival_rate: float
    service_rate: float
    min_devices: int
    buffer: float
    target_wait: Optional[int]

class OperationResult(TypedDict):
    success: bool
    message: str

# default queue management configuration
default_policy_config: Dict[str, PolicyConfig] = {
        "min_wait": PolicyConfig(
            arrival_rate=1.5,
            service_rate=0.5,
            min_devices=1,
            buffer=0.2,
            target_wait=120,
        ),
        "energy_save": PolicyConfig(
            arrival_rate=1.5,
            service_rate=0.5,
            min_devices=1,
            buffer=0.2,
            target_wait=None,  # No target wait for energy save
        ),
    }

# queue management configuration
class QueueManagementConfig(BaseModel):
    current_policy: str = "min_wait"
    current_config: PolicyConfig = default_policy_config[current_policy]

# queue management status
class QueueManagementStatus(BaseModel):
    is_running: bool = False
    status_message: str = ""

def init():
    global qm_config
    global qm_status
    qm_config = QueueManagementConfig()
    qm_status = QueueManagementStatus()


@mcp.tool()
def get_queue_policy() -> list[str]:
    """
    Get the supported queue management policies.

    Args:
        None

    Returns:
        List of supported queue management policy
    """
    return list(default_policy_config.keys())


@mcp.tool()
def get_queue_policy_config(policy: Optional[str] = None) -> Dict[str, PolicyConfig]:
    """
    Get the configuration for all queue management policies. Return the default and updated configuration.
    
    Args:
        policy: List of target policies (None returns all policies configuration)

    Returns:
        Dictionary of queue managment policy configuration keyed by policy name, e.g.:

        Dict["min_wait"].PolicyConfig{
            arrival_rate: 1.5,
            service_rate: 0.5,
            min_devices: 1,
            buffer: 0.2,
            target_wait: 120,
        }
    """
    return default_policy_config

@mcp.tool()
def get_current_queue_policy() -> OperationResult:
    """
    Get current in used/activated queue management policy.

    Args:
        None

    Returns:
        Operation results, e.g.:
        {
            "sucess": True
            "message": "Current selected policy: energy_save"
        }
    """
    return OperationResult(success=True, message=f"Policy '{qm_config.current_policy}' selected successfully.")


@mcp.tool()
def select_queue_policy(policy: str) -> OperationResult:
    """
    select the queue management policy to activate.

    Args:
        policy: name of queue management policy

    Returns:
        Operation results, e.g.:            
            result.sucess=True
            result.sucess=False
    """
    if policy not in get_queue_policy():
        return OperationResult(success=False, message=f"Policy '{policy}' is not supported.")
    
    qm_config.current_policy = policy
    # For this example, we just return success
    return OperationResult(success=True, message=f"Policy '{qm_config.current_policy}' selected successfully.")


@mcp.tool()
def update_queue_policy_config(policy: str, config: PolicyConfig) -> OperationResult:
    """
    Update the queue management policy configuration.

    Args:
        policy: name of queue management policy
        config: configuration of the named queue management policy

    Returns:
        Operation results, e.g.:
            result.success=True
            result.success=False
    """
    if policy not in get_queue_policy():
        return OperationResult(success=False, message=f"Policy '{policy}' is not supported.")
    
    qm_config.current_config = config
    return OperationResult(success=True, message=f"Configuration for policy '{policy}' updated successfully. {qm_config.current_config}")


@mcp.tool()
async def get_queue_length() -> OperationResult:
    """
    Get current queue length.

    Args:
        None

    Returns:
        OperationResult object containing the current queue length.
    """
    current_length = randint(0, 50)  # Placeholder for actual queue length logic
    return OperationResult(success=True, message=str(current_length))


@mcp.tool()
def start_queue_management() -> OperationResult:
    """
    Start the queue management service if the following conditions are met:
    - Queue managment policy has been pre-selected through select_queue_policy(), and
    - Queue managment loop has not started.

    Args:
        None

    Returns:
        Operation results, e.g.:
            result.success=True
            result.success=False
    """
    if qm_config.current_policy is None:
        return OperationResult(success=False, message="No queue management policy selected. Please select a policy first.")
    
    if qm_status.is_running:
        return OperationResult(success=False, message="Queue management service is already running. Please stop the service before starting again.")

    qm_status.is_running = True
    qm_status.status_message = f"Queue management service started with policy '{qm_config.current_policy}' and configuration {qm_config.current_config}."

    # Placeholder for starting the queue management service
    return OperationResult(success=True, message=f"Queue management service started with policy '{qm_config.current_policy}'.")


@mcp.tool()
def stop_queue_management() -> OperationResult:
    """
    Stop the running queue management service. If queue managment service is not running, return operation success.

    Args:
        None

    Returns:
        Operation results, e.g.:
            result.success=True
            result.success=False
    """
    if not qm_status.is_running:
        return OperationResult(success=True, message="Queue management service is not running. No action taken.")
    else:
        # Placeholder for stopping the queue management service
        qm_status.is_running = False
        qm_status.status_message = "Queue management service stopped."
        return OperationResult(success=True, message="Queue management service stopped successfully.")


@mcp.tool()
def get_queue_management_status() -> QueueManagementStatus:
    """
    Get the current status of the queue management service.

    Args:
        None

    Returns:
        QueueManagementStatus object containing the current status of the queue management service.
    """
    return qm_status


if __name__ == "__main__":
    try:
        # The MCP run function ultimately uses asyncio.run() internally
        init()
        mcp.run(transport="streamable-http")

    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
        # The asyncio event loop has already been stopped by the KeyboardInterrupt
        print("Server has been shut down.")

    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

    finally:
        print("Thank you for using the Queue Flow Management MCP Server!")
