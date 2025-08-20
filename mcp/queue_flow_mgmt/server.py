import os
import sys
import ast
import json
import subprocess
from typing import List, Dict, Any, TypedDict, Optional
from pydantic import TypeAdapter
from mcp.server.fastmcp import FastMCP
from quixstreams import Application
from confluent_kafka import TopicPartition


class PolicyConfig(TypedDict):
    arrival_rate: float
    service_rate: float
    min_devices: int = 1 # type: ignore
    buffer: float = 0.2 # type: ignore # 0 - 1
    target_wait: Optional[int] = 120 # type: ignore # in seconds

class OperationResult(TypedDict):
    success: bool
    message: str

class QueueManagementStatus(TypedDict):
    is_running: bool = False # type: ignore
    message: str = "" # type: ignore

PolicyConfigValidator = TypeAdapter(PolicyConfig)

# Initialize FastMCP server
mcp = FastMCP("Queue_Flow_Management", host="localhost", port=6969)

# All policy available
queue_policy = {
    "energy_save": PolicyConfig(
        arrival_rate=1.5,
        service_rate=0.5,
        min_devices=1,
        buffer=0.2,
        target_wait=None # No target wait for energy save
    ),
    "min_wait": PolicyConfig(
        arrival_rate=1.5,
        service_rate=0.5,
        min_devices=1,
        buffer=0.2,
        target_wait=120
    ),
}

# Default policy
selected_policy = [*queue_policy][0]

# Configure an Kafka Application.
# The config params will be used for the Consumer instance too.
kafka_app = Application(
    broker_address="localhost:9092",
    consumer_group="retail",
    auto_offset_reset="latest",
)
latest = 0
kafka_timeout = 10

# Initialize queue management process
global queue_management_process
queue_management_process = None

queue_management_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(queue_management_dir, "qflow.log")
queue_management_script = os.path.join(queue_management_dir, "queue_management_utils.py")


@mcp.tool()
def get_queue_policy() -> list[str]:
    """
    Get the supported queue management policies.

    Args:
        None

    Returns:
        List of supported queue management policy, e.g.: ["energy_save", "min_wait"]
    """
    global queue_policy
    return [*queue_policy]

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
    try:
        global selected_policy
        return OperationResult(
            success=True,
            message=f"Current selected policy: {selected_policy}."
        )
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Failed to get current selected policy. {e}."
        )

@mcp.tool()
def select_queue_policy(policy: str) -> OperationResult:
    """
    Select the queue management policy to activate.

    Args:
        policy (str): Name of queue management policy.

    Returns:
        Operation results, e.g.:
        {
            "sucess": True
            "message": "Current selected policy: energy_save"
        }
    """
    global queue_policy
    if policy not in [*queue_policy]:
        return OperationResult(
            success=False,
            message="Error: Policy not exist."
        )
    
    global selected_policy
    # if selected policy change
    if policy != selected_policy:
        selected_policy = policy

        global queue_management_process
        # if the process is running, restart the process with new selected policy
        if (queue_management_process is not None) or (hasattr(queue_management_process, "poll") and (queue_management_process.poll() is None)): # type: ignore
            stop_queue_management()
            start_queue_management()
            is_running, message = get_queue_management_status()

            if not is_running:
                return OperationResult(
                    success=False,
                    message=f"Current selected policy: {selected_policy}. Failed to restart queue management process. {message}"
                )

    return OperationResult(
        success=True,
        message=f"Current selected policy: {selected_policy}."
    )

@mcp.tool()
def get_policy_config(policy: Optional[List[str] | str] = None) -> Dict[str, PolicyConfig]:
    """
    Get the configuration for all queue management policies. Return the default and updated configuration.
    
    Args:
        policy (list | None): List of target policies. Will returns all policies configuration if policy is None.

    Returns:
        Dictionary of queue management policy configuration keyed by policy name, e.g.:
        {
            "min_wait":
                {
                    arrival_rate: 1.5,
                    service_rate: 0.5,
                    min_devices: 1,
                    buffer: 0.2,
                    target_wait: 120,
                }
        }
    """
    global queue_policy
    all_policy = [*queue_policy]
    if (policy is None) or (not policy):
        policy = all_policy
    if isinstance(policy, str):
        if (policy.lower() == "none") or (policy.lower() == "null") or (policy == "*"):
            policy = all_policy
        else: 
            policy = ast.literal_eval(policy)
    
    config = {}
    for p in policy:  # type: ignore
        if p in all_policy:
            config[p] = queue_policy[p]
    
    return config

@mcp.tool()
def update_policy_config(policy: str, config: str) -> OperationResult: # type: ignore
    """
    Update the queue management policy configuration.

    Args:
        policy (str): Name of queue management policy.
        config (str): Configuration of the named queue management policy in format of JSON string, e.g.:
            {
                "arrival_rate": 1.5,
                "service_rate": 0.5,
                "min_devices": 1,
                "buffer": 0.2,
                "target_wait": 120,
            }

    Returns:
        Operation results, e.g.:
        {
            "sucess": False
            "message": "Error: Policy not exist."
        }
    """
    global queue_policy
    global selected_policy
    if policy not in [*queue_policy]:
        return OperationResult(
            success=False,
            message="Error: Policy not exist."
        )
    
    # convert JSON string to dictionary
    if isinstance(config, str):
        config: PolicyConfig = json.loads(config)
    
    # check dictionary match defined PolicyConfig typeddict
    try:
        config = PolicyConfigValidator.validate_python(config)
    # if dictionary not match with defined PolicyConfig typeddict (certain dictionary keys missing)
    except Exception as e:
        current_config = dict(queue_policy[policy])
        for key in config.keys():
            if key not in current_config:
                return OperationResult(
                    success=False,
                    message=f"Failed to update policy configuration. Invalid key: {key}"
                )
            else:
                current_config[key] = config[key]
        config = current_config # type: ignore
    
    # if the provided configuration is same with old configuration
    if config == queue_policy[policy]:
        return OperationResult(
            success=True,
            message="New policy configuration same with old configuration."
        )

    queue_policy[policy] = config

    if policy == selected_policy:
        global queue_management_process
        # if the process is running, restart the process with new config
        if (queue_management_process is not None) or (hasattr(queue_management_process, "poll") and (queue_management_process.poll() is None)): # type: ignore
            stop_queue_management()
            start_queue_management()
            is_running, message = get_queue_management_status()

            if not is_running:
                return OperationResult(
                    success=False,
                    message=f"Policy configuration update successfully. Failed to restart queue management process. {message}"
                )
            
    return OperationResult(
        success=True,
        message="Policy configuration update successfully."
    )

@mcp.tool()
async def get_queue_length() -> OperationResult:
    """
    Get current queue length.

    Args:
        None

    Returns:
        OperationResult object containing the current queue length, e.g.:
        {
            "sucess": True
            "message": "3"
        }
    """
    global latest
    # Create a consumer and start a polling loop
    with kafka_app.get_consumer() as consumer:
        topic = "people-count"  # specify the topic name
        partition = 0  # adjust if multiple partitions

        # Get the latest offset (high watermark)
        try:
            low, high = consumer.get_watermark_offsets(TopicPartition(topic, partition), timeout=kafka_timeout)
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to get watermark offsets. {e}"
            )

        if high > latest:
            latest = high
        elif high == 0 or high == latest:
            return OperationResult(
                success=False,
                message="No latest queue length."
            )

        # Assign consumer to the latest offset (start consuming new messages only)
        consumer.assign([TopicPartition(topic, partition, high-1)])

        # Poll for new message
        try:
            msg = consumer.poll(0.1, timeout=kafka_timeout)
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to poll new message. {e}"
            )
        
        if msg is None:
            return OperationResult(
                success=False,
                message="No latest queue length."
            )
        elif msg.error():
            return OperationResult(
                success=False,
                message=f"Kafka error: {msg.error()}"
            )

        value = json.loads(msg.value().decode("utf-8")) # type: ignore
        print(f"High: {high}, Latest: {latest}, Received: {value}", flush=True)
        # Do some work with the value here ...
        # Store the offset of the processed message on the Consumer
        # for the auto-commit mechanism.
        # It will send it to Kafka in the background.
        # Storing offset only after the message is processed enables at-least-once delivery
        # guarantees.
        consumer.store_offsets(message=msg)
        consumer.close()
        return OperationResult(
            success=True,
            message=f"{value["queue_count"]}"
        )

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
        {
            "sucess": True
            "message": "Successfully start queue management process."
        }
    """
    # Initialize queue management process
    global queue_policy
    global selected_policy
    global queue_management_process
    # check if the process haven't run
    if (queue_management_process is None) or (hasattr(queue_management_process, "poll") and (queue_management_process.poll() is not None)):
        try:
            log_file = open(log_path, "a", 1)
            queue_management_process = subprocess.Popen(["uv", "run", queue_management_script, "--strategy", selected_policy, "--config", json.dumps(queue_policy)], stdout=log_file, stderr=log_file, bufsize=1)
            return OperationResult(
                success=True,
                message="Successfully start queue management process."
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to start queue management process. {e}"
            )
    
    return OperationResult(
        success=False,
        message="Failed to start queue management process. The process already started."
    )

@mcp.tool()
def stop_queue_management() -> OperationResult:
    """
    Stop the running queue management service. If queue managment service is not running, return operation success.

    Args:
        None

    Returns:
        Operation results, e.g.:
        {
            "sucess": False
            "message": "Failed to stop queue management process."
        }
    """
    global queue_management_process
    # check if the process haven't run
    if (queue_management_process is None) or (hasattr(queue_management_process, "poll") and (queue_management_process.poll() is not None)):
        return OperationResult(
            success=True,
            message="Successfully stop queue management process. The process not running."
        )
    
    try:
        queue_management_process.terminate()
        queue_management_process = None

        with open(log_path, "a", 1) as log_file:
            log_file.write("Queue management process stopped.\n")
            log_file.write("===========================================================\n")
        
        return OperationResult(
            success=True,
            message="Successfully stop queue management process."
        )
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Failed to stop queue management process. {e}"
        )

@mcp.tool()
def get_queue_management_status() -> QueueManagementStatus:
    """
    Get the current status of the queue management service.

    Args:
        None

    Returns:
        QueueManagementStatus object containing the current status of the queue management service, e.g.:
        {
            "is_running": True
            "message": "Queue management process running smooth."
        }
    """
    global queue_management_process
    # if the process not running
    if queue_management_process is None:
        return QueueManagementStatus(
            is_running=False,
            message="The process not running."
        )
    # if the process have error
    if hasattr(queue_management_process, "poll") and (queue_management_process.poll() is not None):
        error_msg = ""
        with open(log_path, "r") as log:
            error_msg = log.readlines()[-1].strip()
        return QueueManagementStatus(
            is_running=False,
            message=f"Exit code: {queue_management_process.poll()}. {error_msg}"
        )
    return QueueManagementStatus(
        is_running=True,
        message="Queue management process running smooth."
    )


if __name__ == "__main__":
    try:
        # Run the server
        mcp.run(transport='streamable-http')

    except KeyboardInterrupt:
        print("Server shutting down gracefully...")
        print("Server has been shut down.")

    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
        
    finally:
        print("Thank you for using the Queue Flow Management MCP Server!")
