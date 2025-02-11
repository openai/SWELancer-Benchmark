# fmt: off
# type: ignore
# ruff: noqa
# isort: skip_file
import asyncio
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import VirtualMachineScaleSetVMInstanceRequiredIDs, VirtualMachineScaleSetVM
from azure.mgmt.network import NetworkManagementClient
import azure.core.exceptions
import csv
import zmq
from time import sleep, time
from filelock import UnixFileLock
from collections import defaultdict
import os
from uuid import uuid4
import backoff
import json

CRON_INTERVAL = 5
MACHINE_HEARTBEAT_TIMEOUT = 60 * 10

SUBSCRIPTION = "f77ebf0b-8875-4050-b702-696473d0468f"  # preparedness-autonenv
credential = DefaultAzureCredential()
compute_client = ComputeManagementClient(credential, SUBSCRIPTION)
network_client = NetworkManagementClient(credential, SUBSCRIPTION)

TARGET_MACHINES_PER_SCALESET = dict()
SCALESET_VM_SKU = dict()

state_socket = zmq.Context().socket(zmq.REQ)
state_socket.connect("ipc:///tmp/alcatraz-cluster-state")
state_socket.setsockopt(zmq.RCVTIMEO, 5000)
print("Connected to state socket")

@backoff.on_exception(backoff.expo, azure.core.exceptions.AzureError, max_tries=4)
async def azure_update_scaleset_vms_by_id(scaleset_name, scaleset_machineid_ips, reimage=False):
    # TODO return False if result has error otherwise True
    vm_ids = [scaleset_machineid_ip.split('$')[1]  for scaleset_machineid_ip in scaleset_machineid_ips]
    if not vm_ids:
        return False
    print("reimage" if reimage else "delete", len(vm_ids), vm_ids)
    scaleset_resource_group = 'alcatraz-swarm-' + scaleset_name.split('-')[0]
    result = await asyncio.to_thread(
        compute_client.virtual_machine_scale_sets.begin_reimage if reimage else compute_client.virtual_machine_scale_sets.begin_delete_instances,
        scaleset_resource_group, scaleset_name, VirtualMachineScaleSetVMInstanceRequiredIDs(instance_ids=vm_ids)
    )
    print("Waiting", scaleset_name, "reimage" if reimage else "delete", len(scaleset_machineid_ips))
    try:
        async with asyncio.timeout(10*60): # TODO do a smaller timeout if we are reimaging and len(scaleset_machineid_ips)/TARGET_MACHINES_PER_SCALESET[scaleset_name] < 0.2
            result = await asyncio.to_thread(result.result)
        print("result", result, scaleset_name, "reimage" if reimage else "delete", len(scaleset_machineid_ips))
    except TimeoutError:
        print("timeout occured during", scaleset_name, "reimage" if reimage else "delete")
        return True
    except Exception as e:
        print("failed to", "reimage" if reimage else "delete", "with exception", str(e))
        return False
    return True

@backoff.on_exception(backoff.expo, azure.core.exceptions.AzureError, max_tries=4)
async def azure_update_scaleset_vm_count(scaleset_name, target_count):
    scaleset_resource_group = 'alcatraz-swarm-' + scaleset_name.split('-')[0]
    vmss = await asyncio.to_thread(
        compute_client.virtual_machine_scale_sets.get,
        scaleset_resource_group, scaleset_name
    )
    vmss.sku.capacity = target_count
    result = await asyncio.to_thread(
        compute_client.virtual_machine_scale_sets.begin_create_or_update,
        scaleset_resource_group, scaleset_name, vmss
    )
    print("Waiting for new vm count", scaleset_name, "target", target_count)
    try:
        result = await asyncio.to_thread(result.result)
        print("result", result)
    except:
        return False # TODO this never really triggers does it :( ?
    return True


async def azure_get_ips_and_machine_ids_from_scaleset(scaleset_name: str):
    scaleset_resource_group = 'alcatraz-swarm-' + scaleset_name.split('-')[0]
    instance_view = list(await asyncio.to_thread(
        compute_client.virtual_machine_scale_set_vms.list,
        scaleset_resource_group,
        scaleset_name
    )) # TODO am I sure this list method doesnt do more requests while iterating (next())?
    # TODO remove
    @backoff.on_exception(backoff.expo, azure.core.exceptions.AzureError)
    async def get_ip_and_machine_id(instance: VirtualMachineScaleSetVM):
        instance_id = instance.instance_id
        nic_id = instance.network_profile.network_interfaces[0].id
        nic_name = nic_id.split("/")[-1]
        nic_rg = nic_id.split("/")[4]
        nic = await asyncio.to_thread(
            network_client.network_interfaces.get_virtual_machine_scale_set_network_interface,
            nic_rg, scaleset_name, instance_id, nic_name
        )
        return (nic.ip_configurations[0].private_ip_address, instance_id)
    return await asyncio.gather(*map(get_ip_and_machine_id, instance_view))

@backoff.on_exception(backoff.expo, azure.core.exceptions.AzureError, max_tries=4)
async def filter_did_not_fail(scaleset_name: str, reimaged_scaleset_machineid_ips):
    scaleset_resource_group = 'alcatraz-swarm-' + scaleset_name.split('-')[0]
    instance_view: list[VirtualMachineScaleSetVM] = list(await asyncio.to_thread(
        compute_client.virtual_machine_scale_set_vms.list,
        scaleset_resource_group,
        scaleset_name
    )) # TODO am I sure this list method doesnt do more requests while iterating (next())?
    vms_in_failed_provisioning_state = set(str(instance.instance_id) for instance in instance_view if instance.provisioning_state == "Failed")
    print("Y", vms_in_failed_provisioning_state, str(instance_view[0].instance_id), set(str(instance.instance_id) for instance in instance_view))
    if vms_in_failed_provisioning_state:
        print(len(vms_in_failed_provisioning_state), "/", len(reimaged_scaleset_machineid_ips), "vms in failed provisioning state for", scaleset_name)
    return [scaleset_machineid_ip for scaleset_machineid_ip in reimaged_scaleset_machineid_ips if scaleset_machineid_ip.split('$')[1] not in vms_in_failed_provisioning_state]

async def scale(scaleset_name, deleted_scaleset_machineid_ips, scaleset_free_machine_count):
    state_socket.send_json({'command': 'GET_ALL'})
    existing = set('$'.join(x.split('$')[:3]) for v in state_socket.recv_json().values() for x in v) # flatten
    print(scaleset_name, deleted_scaleset_machineid_ips, scaleset_free_machine_count)
    if scaleset_free_machine_count + len(deleted_scaleset_machineid_ips) < TARGET_MACHINES_PER_SCALESET[scaleset_name]:
        create_cnt = TARGET_MACHINES_PER_SCALESET[scaleset_name] - scaleset_free_machine_count - len(deleted_scaleset_machineid_ips)
        if create_cnt == 0:
            print("Doing nothing...")
            return
        print("Scale up", scaleset_name, "by", create_cnt, "VMs")
        await azure_update_scaleset_vm_count(scaleset_name, TARGET_MACHINES_PER_SCALESET[scaleset_name])
        all_ips_and_machine_ids = await azure_get_ips_and_machine_ids_from_scaleset(scaleset_name)
        all_scaleset_ips_and_machine_ids = [f"{scaleset_name}${machine_id}${ip}" for ip, machine_id in all_ips_and_machine_ids]
        with open(scaleset_name+".jsonl", 'a') as f:
            f.write(json.dumps(all_scaleset_ips_and_machine_ids) + '\n')
        keys_to_create = [f"{x}${str(uuid4())}" for x in all_scaleset_ips_and_machine_ids if x not in existing]
        state_socket.send_json({
            'command': 'CREATE',
            'keys': keys_to_create,
            'vm_sku': SCALESET_VM_SKU[scaleset_name],
        })
        state_socket.recv_json()
        return
    to_delete_cnt = scaleset_free_machine_count + len(deleted_scaleset_machineid_ips) - TARGET_MACHINES_PER_SCALESET[scaleset_name]
    if await azure_update_scaleset_vms_by_id(scaleset_name, deleted_scaleset_machineid_ips[:to_delete_cnt], reimage=False):
        state_socket.send_json({'command': 'DELETE_KEYS_FROM_DELETED', 'keys': deleted_scaleset_machineid_ips[:to_delete_cnt]})
        state_socket.recv_json()
    reimaged_scaleset_machineid_ips = deleted_scaleset_machineid_ips[to_delete_cnt:]
    if await azure_update_scaleset_vms_by_id(scaleset_name, reimaged_scaleset_machineid_ips, reimage=True):
        reimaged_scaleset_machineid_ips = await filter_did_not_fail(scaleset_name, reimaged_scaleset_machineid_ips) # we only want to assume success if the provisioning state is not Failed
        print("deleting", len(reimaged_scaleset_machineid_ips), "keys for", scaleset_name)
        state_socket.send_json({'command': 'DELETE_KEYS_FROM_DELETED', 'keys': reimaged_scaleset_machineid_ips})
        state_socket.recv_json()
        print("creating", len(reimaged_scaleset_machineid_ips), "keys for", scaleset_name)
        reimaged_ips_and_machine_ids = ['$'.join(x.split('$')[:3])+'$'+str(uuid4()) for x in reimaged_scaleset_machineid_ips]
        state_socket.send_json({
            'command': 'CREATE',
            'keys': reimaged_ips_and_machine_ids,
            'vm_sku': SCALESET_VM_SKU[scaleset_name],
        })
        state_socket.recv_json()
        print("reimage truly complete for", scaleset_name)


async def loop():
    global TARGET_MACHINES_PER_SCALESET, SCALESET_VM_SKU
    print("Starting autoscale loop")
    while True:
        print("Cron alive with interval", CRON_INTERVAL)
        start_time = time()

        with open('config.csv', 'r') as f:
            reader = list(csv.reader(f))
            TARGET_MACHINES_PER_SCALESET = {row[0]: int(row[1]) for row in reader if row}
            SCALESET_VM_SKU = {row[0]: row[2] for row in reader if row}

        print("Killing machines that haven't given heartbeat in", MACHINE_HEARTBEAT_TIMEOUT, "seconds")
        state_socket.send_json({'command': 'KILL_EXPIRED_HEARTBEATS', 'timeout': MACHINE_HEARTBEAT_TIMEOUT})
        print("killed (w/o heartbeat)", state_socket.recv_json()['removed'])

        state_socket.send_json({'command': 'GET_DELETED'})
        deleted: dict[str, int] = state_socket.recv_json()['result']
        mem: dict[str, list[str]] = defaultdict(list)
        for scaleset_machineid_ip, _deleted_timestamp in deleted.items():
            scaleset, _machine_id, _ip, _machine_uuid = scaleset_machineid_ip.split('$')
            mem[scaleset].append(scaleset_machineid_ip)
        
        state_socket.send_json({'command': 'CNT_NON_DELETED_BY_SCALESET'})
        free_machine_count: dict[str, int] = state_socket.recv_json()['result']
        for scaleset_name in TARGET_MACHINES_PER_SCALESET.keys():
            free_machine_count.setdefault(scaleset_name, 0)

        await asyncio.gather(*(scale(scaleset_name, mem[scaleset_name], free_machine_count[scaleset_name]) for scaleset_name in TARGET_MACHINES_PER_SCALESET.keys()))
        if time() - start_time < CRON_INTERVAL:
            await asyncio.sleep(CRON_INTERVAL)


with UnixFileLock(os.path.expanduser('~/lock_autoscale.lock')):
    asyncio.run(loop())
