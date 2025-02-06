# fmt: off
# type: ignore
# ruff: noqa
# isort: skip_file
import zmq
import sys
import json
from collections import deque, defaultdict
from time import time
import atexit

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("ipc:///tmp/alcatraz-cluster-state")
print("Binded socket")
created: dict[str, deque[tuple[str, int]]] = defaultdict(deque)
claiming: dict[str, int] = dict()
claimed: dict[str, tuple[int, int]] = dict()
deleted: dict[str, int] = dict()
try:
    with open('json_state.json', 'r') as file:
        data = json.load(file)
        for k, v in data['created'].items():
            created[k].extend(map(tuple,v))
            print(list(map(tuple,v)))
        claiming.update(data['claiming']); claimed.update({k: tuple(v) for k,v in data['claimed'].items()}); deleted.update(data['deleted'])
except FileNotFoundError:
    print("Data file not found, starting with empty structures.")
except json.JSONDecodeError:
    print("Data file is corrupt or not properly formatted; starting with empty structures.")
    exit(1)

@atexit.register
def save_data():
    with open('json_state.json', 'w') as file:
        json.dump({'created': {k: list(c) for k,c in created.items()}, 'claiming': claiming, 'claimed': claimed, 'deleted': deleted}, file)

# TODO log Requests per 5 second block to appendonly file
def loop():
    while True:
        message = socket.recv_json()
        command = message['command']
        print("recv", command)

        # POST /claim will call these
        if command == 'TRY_TO_CLAIM':
            if not created[message['vm_sku']]:
                socket.send_json({'exception': 'empty'})
                continue
            scaleset_machineid_ip, created_timestamp = created[message['vm_sku']].popleft()
            claiming[scaleset_machineid_ip] = (created_timestamp, time(), message['vm_sku'])
            socket.send_json({'result': scaleset_machineid_ip})
        elif command == 'CLAIM_FAILED':
            created_timestamp, _claim_attempt_timestamp, vm_sku = claiming[message['key']]
            del claiming[message['key']]
            # created[vm_sku].append((message['key'], created_timestamp))
            deleted[message['key']] = time()
            socket.send_json({})
        elif command == 'CLAIM_SUCCEED':
            del claiming[message['key']]
            claimed[message['key']] = (time(), time())
            socket.send_json({})

        # POST /kill_machines will call these
        elif command == 'KILL':
            try:
                del claimed[message['key']]
            except KeyError:
                socket.send_json({'error': 'key not found in claimed'})
                continue
            deleted[message['key']] = time()
            socket.send_json({})

        # POST /im_still_using_machine will call these
        elif command == 'HEARTBEAT':
            try:
                claimed_timestamp, _last_hb_timestamp = claimed[message['key']]
                claimed[message['key']] = (claimed_timestamp, time())
            except KeyError:
                socket.send_json({'error': 'key not found in heartbeat'})
                continue
            socket.send_json({})

        # AUTOSCALE will call these
        elif command == 'GET_DELETED':
            # TODO should we be doing math for delete scalesets here so we can transfer less data over the socket? Should we be precomputing the math with POST /claim /kill so latency is less spiky? I think our use case is fine with latency spiking by 1 second every 5 seconds... and this will probably take < 1 second.
            # At most this is 1 million VMs * 100 bytes = 100 MB. So likely under 1 tenth a second?
            socket.send_json({'result': deleted})
        elif command == 'DELETE_KEYS_FROM_DELETED':
            for k in message['keys']:
                del deleted[k]
            socket.send_json({})
        elif command == 'CNT_NON_DELETED_BY_SCALESET':
            scaleset_cnt: dict[str, int] = defaultdict(int)
            for vm_sku in created:
                for scaleset_machineid_ip, _created_timestamp in created[vm_sku]:
                    scaleset, machine_id, ip, machine_uuid = scaleset_machineid_ip.split('$')
                    scaleset_cnt[scaleset] += 1
            for scaleset_machineid_ip in claiming.keys():
                scaleset, machine_id, ip, machine_uuid = scaleset_machineid_ip.split('$')
                scaleset_cnt[scaleset] += 1
            for scaleset_machineid_ip in claimed.keys():
                scaleset, machine_id, ip, machine_uuid = scaleset_machineid_ip.split('$')
                scaleset_cnt[scaleset] += 1
            socket.send_json({'result': scaleset_cnt})
        elif command == 'CREATE':
            created_timestamp = time()
            created[message['vm_sku']].extend((k, created_timestamp) for k in message['keys'])
            socket.send_json({})
        elif command == 'KILL_EXPIRED_HEARTBEATS':
            t = time()
            removed = []
            for scaleset_machineid_ip, (_claimed_timestamp, last_hb_timestamp) in list(claimed.items()):
                if t - last_hb_timestamp > message['timeout']:
                    del claimed[scaleset_machineid_ip]
                    deleted[scaleset_machineid_ip] = t
                    removed.append(scaleset_machineid_ip)
            claiming_put_back = []
            for scaleset_machineid_ip, (created_timestamp, claim_attempt_timestamp, vm_sku) in list(claiming.items()):
                if t - claim_attempt_timestamp > message['timeout']:
                    del claiming[scaleset_machineid_ip]
                    created[vm_sku].append((scaleset_machineid_ip, created_timestamp))
                    claiming_put_back.append(scaleset_machineid_ip)

            socket.send_json({"removed": removed, "claiming_expired": claiming_put_back})

        
        # GET /status and AUTOSCALE will call these
        elif command == 'GET_ALL':
            socket.send_json({'created': list(m for vm_sku in created for m, _ in created[vm_sku]), 'claiming': list(claiming.keys()), 'claimed': list(claimed.keys()), 'deleted': list(deleted.keys())})
        
        # PROGRAMMING ERR
        else:
            socket.send_json({'error': 'unsupported command'})

try:
    loop()
except KeyboardInterrupt:
    print("Received KeyboardInterrupt.")
    sys.exit(0)  # This ensures atexit functions are called
