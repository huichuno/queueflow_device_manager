from random import randint
from mcp.server.fastmcp import FastMCP
import sys
from typing import List, Dict, TypedDict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceInfo(TypedDict):
    guid: str
    dev_id: str
    hostname: str
    ip_addr: str
    pwr_status: str  # "on", "off", "unknown"

class OperationResult(TypedDict):
    guid: str
    dev_id: str
    success: bool
    message: str

mcp = FastMCP("mock_queuflow_mgmt", host="localhost", port=6970)

default_devices = {
            "Device 01": {
                "guid": "6eed526c-03b5-40cc-b12c-c8845757a7c2",
                "dev_id": "Device 01",
                "hostname": "lenovo",
                "ip_addr": "192.168.0.146",
                "pwr_status": "on"
            },
            "Device 02": {
                "guid": "123e4567-e89b-12d3-a456-426614174000",
                "dev_id": "Device 02",
                "hostname": "asus",
                "ip_addr": "192.168.0.155",
                "pwr_status": "on"
            },
            "Device 03": {
                "guid": "b3f8c9e2-7d4a-4f5b-9a3e-2c6f7d8e9b1a",
                "dev_id": "Device 03",
                "hostname": "adlink",
                "ip_addr": "192.168.0.165",
                "pwr_status": "off"
            }
        }

@mcp.tool()
async def query_devices(dev_ids: Optional[List[str] | str] = None) -> Dict[str, DeviceInfo] | str:
    """
    Get status information for target devices.
    
    Args:
        dev_ids (list | None): List of target device IDs, e.g. ['Device 01', 'Device 02']. Will returns all managed devices if dev_id is None.

    Returns:
        Dict[str, DeviceInfo]: Dictionary of device information keyed by device ID, e.g.:
        {
            "Device 01": {
                "guid": "6eed526c-03b5-40cc-b12c-c8845757a7c2",
                "dev_id": "Device 01",
                "hostname": "lenovo",
                "ip_addr": "192.168.0.146",
                "pwr_status": "on"
            }, 
            "Device 02": {
                "guid": "123e4567-e89b-12d3-a456-426614174000",
                "dev_id": "Device 02",
                "hostname": "asus",
                "ip_addr": "192.168.0.155",
                "pwr_status": "off"
            }
        }
    """
    if dev_ids is None:
        return default_devices # type: ignore
    
    return default_devices if isinstance(dev_ids, str) else {dev_id: default_devices[dev_id] for dev_id in dev_ids if dev_id in default_devices} # type: ignore

@mcp.tool()
async def power_on_devices(dev_ids: Optional[List[str] | str] = None) -> List[OperationResult] | str:
    """
    Power on target devices.
    
    Args:
        dev_ids (list | None): List of device IDs to power on, e.g.: ['Device 01', 'Device 02']. Will power on all devices if dev_id is None.
        
    Returns:
        List[OperationResult]: List of individual operation result for each device, e.g.:
        [
            {
                "guid": "6eed526c-03b5-40cc-b12c-c8845757a7c2",
                "dev_id": "dev01",
                "success": true,
                "message": "Power on successfully.",
            }, 
            {
                "guid": "123e4567-e89b-12d3-a456-426614174000",
                "dev_id": "dev02",
                "success": false,
                "message": "Power on failed.",
            }
        ]
    """
    if dev_ids is None:
        dev_ids = list(default_devices.keys())
    elif isinstance(dev_ids, str):
        dev_ids = [dev_ids]

    results = []
    for dev_id in dev_ids:
        if dev_id in default_devices:
            device = default_devices[dev_id]
            if device["pwr_status"] == "off":
                device["pwr_status"] = "on"
                results.append(OperationResult(guid=device["guid"], dev_id=dev_id, success=True, message="Power on successfully."))
            else:
                results.append(OperationResult(guid=device["guid"], dev_id=dev_id, success=False, message="Device already powered on."))
        else:
            results.append(OperationResult(guid="", dev_id=dev_id, success=False, message="Device not found."))

    return results


@mcp.tool()
async def power_off_devices(dev_ids: Optional[List[str] | str] = None) -> List[OperationResult] | str:
    """
    Power off target devices.
    
    Args:
        dev_ids (list | None): List of device IDs to power off, e.g.: ['Device 01', 'Device 02']. Will power off all devices if dev_id is None.
        
    Returns:
        List[OperationResult]: List of individual operation result for each device, e.g.:
        [
            {
                "guid": "6eed526c-03b5-40cc-b12c-c8845757a7c2",
                "dev_id": "dev01",
                "success": true,
                "message": "Power off successfully.",
            }, 
            {
                "guid": "123e4567-e89b-12d3-a456-426614174000",
                "dev_id": "dev02",
                "success": false,
                "message": "Power off failed.",
            }
        ]
    """
    if dev_ids is None:
        dev_ids = list(default_devices.keys())
    elif isinstance(dev_ids, str):
        dev_ids = [dev_ids]

    results = []
    for dev_id in dev_ids:
        if dev_id in default_devices:
            device = default_devices[dev_id]
            if device["pwr_status"] == "on":
                device["pwr_status"] = "off"
                results.append(OperationResult(guid=device["guid"], dev_id=dev_id, success=True, message="Power off successfully."))
            else:
                results.append(OperationResult(guid=device["guid"], dev_id=dev_id, success=False, message="Device already powered off."))
        else:
            results.append(OperationResult(guid="", dev_id=dev_id, success=False, message="Device not found."))

    return results


if __name__ == "__main__":
    try:
        mcp.run(transport="streamable-http")

    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
        # The asyncio event loop has already been stopped by the KeyboardInterrupt
        print("Server has been shut down.")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

    finally:
        print("Thank you for using the Device Management Toolkit MCP Server!")
