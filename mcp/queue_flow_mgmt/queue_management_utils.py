import os
import sys
import time
import argparse
import json
import asyncio
import dmt_utils
from dotenv import load_dotenv
from server import queue_policy, get_queue_length


load_dotenv()

# authorize the DMT session
asyncio.run(dmt_utils.authorize())
# get all device in the network
asyncio.run(dmt_utils.get_all_device())

global kafka_interval
kafka_interval = os.getenv("kafka_interval", 3) # in seconds

    
def energy_save(
        queue_length: int, 
        arrival_rate: float, 
        service_rate: float, 
        current_active: int, 
        max_devices: int,
        min_devices: int = 1,
        buffer = 0.2,
        target_wait = None,
    ) -> int:
    if (current_active < min_devices):
        return min_devices 
    
    offered_load = arrival_rate / service_rate   
    buffer = max(1, buffer * offered_load)  # Dynamic buffer (20% of N)
    
    if current_active < max_devices and queue_length > (offered_load + buffer):
        return current_active + 1
    elif current_active > min_devices and queue_length < (offered_load - buffer):
        return current_active - 1
    return current_active

def min_wait(
        queue_length: int, 
        arrival_rate: float, 
        service_rate: float, 
        current_active: int, 
        max_devices: int, 
        min_devices: int = 1,
        buffer = 0.2,
        target_wait = 120,
    ) -> int:
    """
    Dynamically adjusts active devices to maintain wait times below target.
    Expands when wait exceeds target, reduces when system is underutilized.
    """
    # Convert target to minutes
    target_min = target_wait / 60
    
    # Calculate current capacity and utilization
    capacity = current_active * service_rate
    utilization = arrival_rate / capacity if capacity > 0 else float('inf')
    
    # Calculate current wait time (minutes)
    net_capacity = capacity - arrival_rate
    current_wait = float('inf') if net_capacity <= 0 else queue_length / net_capacity
    
    # 1. Reduce devices if underutilized and safe
    if current_active > min_devices:
        reduction_threshold = target_min * (1 - buffer)
        if utilization < 0.7 and current_wait < reduction_threshold:
            # Test with one less device
            test_capacity = (current_active - 1) * service_rate - arrival_rate
            if test_capacity > 0 and queue_length / test_capacity <= target_min:
                return current_active - 1
    
    # 2. Add devices if wait exceeds target
    if current_wait > target_min or utilization >= 1:
        # Find minimum devices that meet wait target
        for devices in range(current_active + 1, max_devices + 1):
            test_capacity = devices * service_rate - arrival_rate
            if test_capacity > 0 and queue_length / test_capacity <= target_min:
                return devices
        return max_devices  # Return max if target can't be met
    
    # 3. Maintain current configuration
    return current_active

def calculate_devices(strategy: str, arrival_rate, service_rate, queue_length, current_active, max_devices, min_devices, buffer, target_wait):
    if strategy.lower() == "energy_save":
        return energy_save(queue_length, arrival_rate, service_rate, current_active, max_devices, min_devices, buffer, target_wait)
    elif strategy.lower() == "min_wait":
        return min_wait(queue_length, arrival_rate, service_rate, current_active, max_devices, min_devices, buffer, target_wait)
    raise ValueError(f"Unknown strategy: {strategy}")

def manage_queue(strategy: str, config: str):
    while True:
        queue_length_result = asyncio.run(get_queue_length())
        # if fail to get queue_length, raise error
        if not queue_length_result["success"]: 
            raise Exception(f"Failed to get queue length. {queue_length_result['message']}")
        queue_length = int(queue_length_result["message"])
        print(f"Queue Length: {queue_length}", flush=True)

        all_device = dmt_utils.all_device
        # if get error message instead of device list
        if isinstance(all_device, str): 
            raise Exception(f"Failed to get available device. {all_device}")
        max_devices = len(all_device)
        print(f"Max Devices: {max_devices}", flush=True)

        policies = json.loads(config)
        arrival_rate, service_rate, min_devices, buffer, target_wait = policies[strategy].values()
        print(f"Min Devices: {min_devices}", flush=True)
        print(f"Arrival Rate: {arrival_rate}", flush=True)
        print(f"Service Rate: {service_rate}", flush=True)
        print(f"Buffer: {buffer}", flush=True)
        print(f"Target Wait: {target_wait} {'seconds' if target_wait else ''}", flush=True)
        print(f"Strategy: {strategy}", flush=True)

        current_active = 0
        active_devices = []
        inactive_devices = []
        for device_name in all_device.keys():
            if all_device[device_name]["pwr_status"] == "on":
                active_devices.append(device_name)
                current_active = current_active + 1
            else:
                inactive_devices.append(device_name)
        print(f"Current Active: {current_active}", flush=True)

        try:
            device_required = calculate_devices(strategy, arrival_rate, service_rate, queue_length, current_active, max_devices, min_devices, buffer, target_wait)
            print(f"Device Required: {device_required}", flush=True)
        except Exception as e:
            raise Exception(f"Failed to get device required. {e}")

        # perform power action if device_required != current_active
        results = []
        if device_required > current_active:
            diff = device_required - current_active
            print(f"Power on devices: {','.join(inactive_devices[:diff])}", flush=True)
            results = asyncio.run(dmt_utils.power_on_devices(inactive_devices[:diff]))
        if device_required < current_active:
            diff = current_active - device_required
            print(f"Power off devices: {','.join(active_devices[:diff])}", flush=True)
            results = asyncio.run(dmt_utils.power_off_devices(active_devices[:diff]))

        # check power action results
        for result in results:
            guid, dev_id, success, message = result.values()
            if success:
                print(f"{dev_id} (GUID: {guid}). {message}", flush=True)
            else:
                raise Exception(f"{dev_id} (GUID: {guid}). {message}")

        print("===========================================================", flush=True)
        time.sleep(kafka_interval)

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="queue_management_utils.py",
        description="Manage queue.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("-s", "--strategy", action="store", default="energy_save", help="Strategy used to manage queue.")
    parser.add_argument("-c", "--config", action="store", default=json.dumps(queue_policy), help="Available queue policies and their configuration.")

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])

    print("Queue management process started.", flush=True)
    print("===========================================================", flush=True)
    manage_queue(strategy=args.strategy, config=args.config)
