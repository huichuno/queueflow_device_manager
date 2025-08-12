import os
import asyncio
import ast
import sys
from dotenv import load_dotenv
from typing import Any, List, Dict, TypedDict, Optional
import httpx
from mcp.server.fastmcp import FastMCP


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


# Initialize FastMCP server
mcp = FastMCP("Device Management Toolkit", host="localhost", port=6970)

# Constants
DMT_API_BASE = "http://localhost:8181/api/v1"
USER_AGENT = "DMT-app/1.0"

load_dotenv()
DMT_username = os.getenv("DMT_username")
DMT_password = os.getenv("DMT_password")

global token
global all_device

async def get_token(username: str, password: str) -> str | None:
    """
    Generates a JWT token that can be used for authentication to both MPS and RPS APIs. 
    Refer https://device-management-toolkit.github.io/docs/2.27/GetStarted/Enterprise/setup/#configuration for more information.

    Args:
        username (str): Intel® DMT username.
        password (str): Intel® DMT password.
    """
    url = f"{DMT_API_BASE}/authorize"
    payload = {
        "username": username,
        "password": password
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data["token"]
        except Exception:
            return None

async def authorize():
    global token
    token = await get_token(DMT_username, DMT_password) # type: ignore


async def make_dmt_get_request(url: str) -> dict[str, Any] | None:
    """Make a GET request to the Intel® DMT API with proper error handling."""
    global token
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"Exception": e}

async def make_dmt_post_request(url: str, json: dict[str, Any]) -> dict[str, Any] | None:
    """Make a POST request to the Intel® DMT API with proper error handling."""
    global token
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=json, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"Exception": e}


async def get_power_state(guid: str) -> str:
    """ 
    Retrieve current power state of device. Possible power state values:
        2 = on - corresponding to ACPI state G0 or S0 or D0
        8 = off - corresponding to ACPI state G2, S5, or D3

    Args:
        guid (str): GUID of device.
    
    Returns:
        str: Power state of the device.
    """
    url = f"{DMT_API_BASE}/amt/power/state/{guid}"
    data = await make_dmt_get_request(url)

    if data.get("Exception"): # type: ignore
        return f"Unable to get power state of device. Exception: {data['Exception']}" # type: ignore
    
    match data["powerstate"]: # type: ignore
        case 2: return "on"
        case 8: return "off"
        case _: return "unknown"

async def get_ip(guid: str) -> str:
    """ 
    Retrieve the IP address of device.

    Args:
        guid (str): GUID of device.

    Returns:
        str: IP address of the device.
    """
    url = f"{DMT_API_BASE}/amt/networkSettings/{guid}"
    data = await make_dmt_get_request(url)

    if data.get("Exception"): # type: ignore
        return f"Unable to get IP address of device. Exception: {data['Exception']}" # type: ignore
    if (not data["wired"]["ipAddress"]) and (not data["wireless"]["ipAddress"]): # type: ignore
        return "No IP address for the device."
    if data["wired"]["ipAddress"]: # type: ignore
        return data["wired"]["ipAddress"] # type: ignore
    else:
        return data["wireless"]["ipAddress"] # type: ignore

async def discover_device() -> Dict[str, DeviceInfo] | str:
    """
    Discover all connected devices in the network.

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
    status = 1 # status of the client. '0' = disconnected devices, '1' = connected devices
    url = f"{DMT_API_BASE}/devices?status={status}"
    data = await make_dmt_get_request(url)

    if not isinstance(data, list) and data.get("Exception"): # type: ignore
        return f"Unable to fetch devices. Exception: {data['Exception']}" # type: ignore
    if isinstance(data, list) and len(data) < 1:
        return "No device."

    devices = {}
    for item in data: # type: ignore
        device: DeviceInfo = {
            "guid": item["guid"], # type: ignore
            "dev_id": item["friendlyName"], # type: ignore
            "hostname": item["hostname"], # type: ignore
            "ip_addr": await get_ip(item["guid"]), # type: ignore
            "pwr_status": await get_power_state(item["guid"]) # type: ignore
        }
        devices[item["friendlyName"]] = device # type: ignore

    return devices

async def get_all_device():
    global all_device
    all_device = await discover_device()


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
    global all_device
    if (dev_ids is None) or (not dev_ids):
        return all_device
    if isinstance(dev_ids, str):
        if (dev_ids.lower() == "none") or (dev_ids.lower() == "null") or (dev_ids == "*"):
            return all_device
        else:
            dev_ids = ast.literal_eval(dev_ids)

    devices = {}
    for dev_id in dev_ids: # type: ignore
        devices[dev_id] = all_device[dev_id] # type: ignore
    
    return devices

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
    global all_device
    if (dev_ids is None) or (not dev_ids):
        dev_ids = all_device.keys() # type: ignore
    if isinstance(dev_ids, str):
        if (dev_ids.lower() == "none") or (dev_ids.lower() == "null") or (dev_ids == "*"):
            dev_ids = all_device.keys() # type: ignore
        else: 
            dev_ids = ast.literal_eval(dev_ids)

    results = []
    payload = {
        "action": 2,
        "useSOL": "false"
    }
    for dev_id in dev_ids: # type: ignore
        guid = all_device[dev_id]["guid"] # type: ignore
        url = f"{DMT_API_BASE}/amt/power/action/{guid}"
        data = await make_dmt_post_request(url, json=payload)

        if data.get("ReturnValue") is None: # type: ignore
            result: OperationResult = {
                "guid": guid,
                "dev_id": dev_id,
                "success": False,
                "message": "Unable to power on the device."
            }
        if data.get("Exception"): # type: ignore
            result: OperationResult = {
                "guid": guid,
                "dev_id": dev_id,
                "success": False,
                "message": f"Unable to power on the device. Exception: {data['Exception']}" # type: ignore
            }
        if data["ReturnValue"] != 0: # type: ignore
            result: OperationResult = {
                "guid": guid,
                "dev_id": dev_id,
                "success": False,
                "message": "Power on failed."
            }
        else:
            result: OperationResult = {
                "guid": guid,
                "dev_id": dev_id,
                "success": True,
                "message": "Power on successfully."
            }
            all_device[dev_id]["pwr_status"] = "on" # type: ignore
        
        results.append(result)

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
    global all_device
    if (dev_ids is None) or (not dev_ids):
        dev_ids = all_device.keys() # type: ignore
    if isinstance(dev_ids, str):
        if (dev_ids.lower() == "none") or (dev_ids.lower() == "null") or (dev_ids == "*"):
            dev_ids = all_device.keys() # type: ignore
        else: 
            dev_ids = ast.literal_eval(dev_ids)

    results = []
    payload = {
        "action": 8,
        "useSOL": "false"
    }
    for dev_id in dev_ids: # type: ignore
        guid = all_device[dev_id]["guid"] # type: ignore
        url = f"{DMT_API_BASE}/amt/power/action/{guid}"
        data = await make_dmt_post_request(url, json=payload)

        if data.get("ReturnValue") is None: # type: ignore
            result: OperationResult = {
                "guid": guid,
                "dev_id": dev_id,
                "success": False,
                "message": "Unable to power off the device."
            }
        if data.get("Exception"): # type: ignore
            result: OperationResult = {
                "guid": guid,
                "dev_id": dev_id,
                "success": False,
                "message": f"Unable to power off the device. Exception: {data['Exception']}" # type: ignore
            }
        if data["ReturnValue"] != 0: # type: ignore
            result: OperationResult = {
                "guid": guid,
                "dev_id": dev_id,
                "success": False,
                "message": "Power off failed."
            }
        else:
            result: OperationResult = {
                "guid": guid,
                "dev_id": dev_id,
                "success": True,
                "message": "Power off successfully."
            }
            all_device[dev_id]["pwr_status"] = "off" # type: ignore
        
        results.append(result)

    return results

if __name__ == "__main__":
    try:
        # authorize the session
        asyncio.run(authorize())
        # get all device in the network
        asyncio.run(get_all_device())

        mcp.run(transport='streamable-http')

    except KeyboardInterrupt:
        print("Server shutting down gracefully...")
        print("Server has been shut down.")

    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

    finally:
        print("Thank you for using the Device Management Toolkit MCP Server!")