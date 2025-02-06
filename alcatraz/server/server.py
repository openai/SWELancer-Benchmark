# fmt: off
# type: ignore
# ruff: noqa
# isort: skip_file
import csv
from time import time
from collections import defaultdict

# sudo pip3.11 install requests fastapi azure-identity azure-mgmt-compute azure-mgmt-network backoff pyzmq
from fastapi.responses import HTMLResponse
import requests
import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException
import zmq
import os

state_socket = None
SWARM_PROXY_HOST = os.getenv("SWARM_PROXY_HOST", "swarm-proxy.alcatraz.openai.org")
MACHINE_HEARTBEAT_TIMEOUT = int(os.getenv("MACHINE_HEARTBEAT_TIMEOUT", 60*20))

async def claim_machine(machine_info: str, user_provided_ssh_key: str):
    try:
        print("claiming", machine_info)
        response = await asyncio.to_thread(
            requests.post,
            f"http://{SWARM_PROXY_HOST}/proxy/health",
            json={"machine_info": machine_info, "user_provided_ssh_key": user_provided_ssh_key},
            timeout=20,
        )
        return response.status_code == 200
    except Exception as e:
        print('claim error', machine_info)
        print(e)
        return False


app = FastAPI()

@app.on_event("startup")
async def startup_event():
    global state_socket
    state_socket = zmq.Context().socket(zmq.REQ)
    state_socket.connect("ipc:///tmp/alcatraz-cluster-state")
    state_socket.setsockopt(zmq.RCVTIMEO, 5000) # 5,000 ms
    print("Connected to state socket")

@app.on_event("shutdown")
async def shutdown_event():
    state_socket.close()
    print("Closed state socket")


buckets = {}
capacity = 1000  # Max tokens in the bucket (max burst)
refill_rate = 1000  # Tokens per second


def get_token(user_id):
    """Token bucket algorithm"""
    current_time = time()
    tokens, last_time = buckets.get(user_id, (capacity, current_time))

    elapsed = current_time - last_time
    increment = elapsed * refill_rate
    tokens = min(capacity, tokens + increment)

    if tokens >= 1:
        buckets[user_id] = (tokens - 1, current_time)
        return True
    else:
        return False


@app.post("/claim_machines/")
async def claim_machines_route(
    num_machines: int, untrusted_user_provided_id: str, vm_sku: str = 'Standard_D2as_v4', user_provided_ssh_key: str = ""
):
    """Claim at most num_machines for client"""
    if num_machines < 1:
        raise HTTPException(status_code=400, detail="num_machines must atlease one")
    if get_token(untrusted_user_provided_id):
        async def f():
            for _ in range(3):
                state_socket.send_json({'command': 'TRY_TO_CLAIM', 'vm_sku': vm_sku})
                result = state_socket.recv_json()
                if result.get('exception', None) == 'empty':
                    return None
                scaleset_machineid_ip = result['result'] # is there a way to asyncify this? Like it should be a connection pool? or do we just assume its fast enough?
                if await claim_machine(scaleset_machineid_ip, user_provided_ssh_key):
                    state_socket.send_json({'command': 'CLAIM_SUCCEED', 'key': scaleset_machineid_ip})
                    state_socket.recv_json()
                    return scaleset_machineid_ip
                else:
                    state_socket.send_json({'command': 'CLAIM_FAILED', 'key': scaleset_machineid_ip})
                    state_socket.recv_json()
            return None
        claimed_machines = list(filter(None, await asyncio.gather(*[f() for _ in range(num_machines)])))
        # TODO mark as owned by user in redis
        return {"claimed_machines": claimed_machines}
    else:
        raise HTTPException(status_code=429, detail="Too many requests")

@app.post("/kill_machines/")
async def kill_machines_route(scaleset_machineid_ips: str):
    # TODO asyncify? or batch kill? etc...
    for scaleset_machineid_ip in scaleset_machineid_ips.split(','):
        if scaleset_machineid_ip.count('$') != 3:
            raise HTTPException(status_code=422, detail=f"scaleset_machineid_ip not of valid form: {scaleset_machineid_ip}")
        state_socket.send_json({'command': 'KILL', 'key': scaleset_machineid_ip})
        if 'error' in state_socket.recv_json():
            raise HTTPException(status_code=404, detail=f"scaleset_machineid_ip {scaleset_machineid_ip} not found. Others may have been deleted")
    return {"message": "Machines killed"}

@app.post("/im_still_using_machine/")
async def heartbeat(scaleset_machineid_ips: str):
    t = time()
    for scaleset_machineid_ip in scaleset_machineid_ips.split(','):
        if scaleset_machineid_ip.count('$') != 3:
            raise HTTPException(status_code=422, detail=f"scaleset_machineid_ip not of valid form: {scaleset_machineid_ip}")
        state_socket.send_json({'command': 'HEARTBEAT', 'key': scaleset_machineid_ip})
        if 'error' in state_socket.recv_json():
            raise HTTPException(status_code=404, detail=f"scaleset_machineid_ip {scaleset_machineid_ip} not found. Others may have been heartbeated")
    return {"message": "Heartbeat(s) acknowledged"}

@app.get("/status/")
async def status():
    with open('config.csv', 'r') as f:
        reader = list(csv.reader(f))
        target_machines_per_scaleset = {row[0]: int(row[1]) for row in reader if row}
        scaleset_vm_sku = defaultdict(lambda : "scaleset scaling down")
        for row in reader:
            if row:
                scaleset_vm_sku[row[0]] = row[2]
    # TODO the more people have status opened, the slower state.py will get
    html = "<html><head><title>Swarm Cluster</title></head><body>"
    # table
    html += "note: deleted means the vm is marked for deletion<table border='1'><tr><th>Scale Set Name</th><th>Azure VM SKU</th><th>Free</th><th>Claiming</th><th>Claimed</th><th>Deleted</th></tr>"
    state_socket.send_json({'command': 'GET_ALL'})
    _data = state_socket.recv_json()
    scaleset_counts = defaultdict(lambda : defaultdict(int))
    # scaleset to dict of (created/claiming/claimed/deleted) to count
    for k in _data:
        for scaleset_machineid_ip in _data[k]:
            scaleset, machine_id, ip, machine_uuid = scaleset_machineid_ip.split('$')
            scaleset_counts[scaleset][k] += 1
    for scaleset_name, counts in scaleset_counts.items():
        html += f"<tr><td>{scaleset_name}</td><td>{scaleset_vm_sku[scaleset_name]}</td><td>{counts['created']}</td><td>{counts['claiming']}</td><td>{counts['claimed']}</td><td>{counts['deleted']}</td></tr>"
    html += f"<tr><td><strong>Total</strong></td><td></td>"
    for _k in ['created', 'claiming', 'claimed', 'deleted']:
        html += f"<td>{sum(counts[_k] for counts in scaleset_counts.values())}</td>"
    html += "</tr>"
    html += "</table>"

    # automatic refresh
    html += "<div id='countdown'></div>"
    html += """<script>
let secondsRemaining = 10;
let countdownInterval = setInterval(function() {
    secondsRemaining--;
    document.getElementById("countdown").innerHTML = "Refreshing in " + secondsRemaining + " seconds";
    if (secondsRemaining <= 0) {
        location.reload();
    }
}, 1000);</script>"""
    html += "</body></html>"
    return HTMLResponse(content=html)


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=80, reload=False, workers=16)
