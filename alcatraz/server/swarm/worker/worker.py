# fmt: off
# type: ignore
# ruff: noqa
# isort: skip_file

import asyncio
import base64
import importlib
import logging
import os
import platform
import pty
import select
import subprocess
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime

import msgpack
import pydantic

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
app = FastAPI()


def encode_extras(obj):
    if isinstance(obj, datetime):
        return {"__datetime__": True, "as_str": obj.isoformat()}
    return obj


def decode_extras(obj):
    if "__datetime__" in obj:
        return datetime.fromisoformat(obj["as_str"])
    return obj


def save_ssh_key(public_ssh_key):
    if platform.system() != "Darwin":
        with open("/home/azureuser/.ssh/authorized_keys", "a") as f:
            f.write(f"\n{public_ssh_key}")


@app.post("/health")
async def health(request: Request) -> Response:
    data = await request.json()
    if data.get("user_provided_ssh_key", None):
        save_ssh_key(data["user_provided_ssh_key"])
        return Response(content="Public SSH key added successfully", status_code=200)
    return Response(content="No SSH key provided but I'm otherwise healthy.", status_code=200)


@app.get("/health")
async def health_get() -> str:
    return "I am a healthy machine. POST to set public ssh key."


container_instance = None


def dynamic_import(module_name, code_str):
    module_list = []
    for i in range(module_name.count(".") + 1):
        partial = ".".join(module_name.split(".")[: i + 1])
        print(partial)
        spec = importlib.util.spec_from_loader(partial, loader=None)
        module = importlib.util.module_from_spec(spec)
        sys.modules[partial] = module
        module_list.append(module)
    for i, m in enumerate(module_list[:-1]):
        setattr(m, module_name.split(".")[i + 1], module_list[i + 1])
    exec(code_str, sys.modules[module_name].__dict__)
    exec(f"import {module_name}", globals())


@app.post("/load_module")
async def load_module(request: Request):
    global container_instance
    if container_instance:
        try:
            await container_instance.__aexit__(None, None, None)
        except:
            pass
    data = await request.json()
    if "init_args" not in data or not isinstance(data["init_args"], dict):
        raise HTTPException(status_code=422, detail="Missing init_args dict field in json body")
    if "code" not in data or not isinstance(data["code"], dict):
        raise HTTPException(status_code=422, detail="Missing code dict field in json body")
    if "pip_install" not in data or not isinstance(data["pip_install"], list):
        raise HTTPException(status_code=422, detail="Missing pip_install list field in json body")
    if "alcatraz.clusters.local" not in data["code"]:
        raise HTTPException(
            status_code=422,
            detail="Missing alcatraz.clusters.local in code field dict in json body",
        )
    if data["pip_install"]:
        try:
            subprocess.run(
                ([] if platform.system() == "Darwin" else ["sudo", "-u", "azureuser"])
                + [sys.executable, "-m", "pip", "install"]
                + data["pip_install"],
                check=True,
            )
            old_pydantic_version = pydantic.__version__
            pydantic_modules = [k for k in sys.modules if k.startswith("pydantic")]
            for k in pydantic_modules:
                del sys.modules[
                    k
                ]  # importlib.reload would have used cached copy... so we force delete here and use normal import
            exec("import pydantic")  # otherwise python complains we ue a var before it's defined
            print("pydantic version", old_pydantic_version, "->", pydantic.__version__)
        except Exception as e:
            return Response(
                content=f"[worker] error when doing pip install: {str(e)}", status_code=500
            )
    try:
        for module_name, code_str in data["code"].items():
            dynamic_import(module_name, code_str)
        # TODO inject logger to be
        # cloud_logger = # sends logs back to client side
        # setattr(sys.modules["alcatraz.clusters.local"], "logger", cloud_logger)
        container_instance = await alcatraz.clusters.local.LocalCluster(  # noqa
            **data["init_args"]
        ).__aenter__()
        return JSONResponse(
            content={"message": "Modules loaded and object instantiated."},
            media_type="application/octet-stream",
        )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            content={
                "exception_traceback": traceback.format_exc(),
                "exception_type": type(e).__name__,
                "exception_message": str(e),
            },
            status_code=580,
        )


@app.post("/get_logs")
async def get_logs():
    return Response(
        content=str(
            subprocess.run(
                ["sudo", "journalctl", "-u", "worker.service", "--no-pager"],
                stdout=subprocess.PIPE,
                text=True,
            ).stdout
        )
    )


tasks = {}


@app.middleware("http")
async def idempotency(request: Request, call_next):
    if "x-idempotency-key" in request.headers and "x-idempotency-expiry" in request.headers:
        idempotency_key = request.headers["x-idempotency-key"]
        idempotency_expiry = request.headers["x-idempotency-expiry"]
        try:
            uuid.UUID(idempotency_key, version=4)
        except:
            raise HTTPException(status_code=422, detail="Idempotency key must be UUIDv4")
        try:
            idempotency_expiry = int(idempotency_expiry)
        except:
            raise HTTPException(status_code=422, detail="Idempotency expiry must be integer")
        if idempotency_key in tasks:
            status_code, content, response_media_type, response_headers = await tasks[
                idempotency_key
            ]["future"]
        else:
            future = asyncio.get_event_loop().create_future()
            expiration_timestamp = time.time() + idempotency_expiry
            tasks[idempotency_key] = {
                "future": future,
                "expiration_timestamp": expiration_timestamp,
            }
            try:
                response = await call_next(request)
            except Exception as e:
                future.set_exception(e)
                raise
            response_body = b"".join([chunk async for chunk in response.body_iterator])
            status_code, content, response_media_type, response_headers = (
                response.status_code,
                response_body,
                response.media_type,
                response.headers,
            )
            future.set_result((status_code, content, response_media_type, response_headers))
        return Response(
            status_code=status_code,
            content=content,
            media_type=response_media_type,
            headers=response_headers,
        )

    else:
        return await call_next(request)


shutdown_event = asyncio.Event()


@app.on_event("startup")
async def startup():
    asyncio.create_task(cleanup_expired_tasks())


@app.on_event("shutdown")
async def shutdown():
    shutdown_event.set()


async def cleanup_expired_tasks():
    while not shutdown_event.is_set():
        current_time = time.time()
        expired_keys = [key for key, d in tasks.items() if current_time > d["expiration_timestamp"]]
        for key in expired_keys:
            print("deleting idempotency key result for key", key)
            del tasks[key]
        await asyncio.sleep(10)


@app.post("/call_method")
async def call_method(request: Request):
    if container_instance is None:
        raise HTTPException(status_code=400, detail="No instance loaded.")
    data = await request.json()
    method_name = data["method"]
    args = data["args"]
    kwargs = data["kwargs"]
    try:
        if isinstance(args, str):
            args = msgpack.unpackb(base64.b64decode(args), object_hook=decode_extras)
        if isinstance(kwargs, str):
            kwargs = msgpack.unpackb(base64.b64decode(kwargs), object_hook=decode_extras)
    except Exception as e:
        print(e)
        raise
    try:
        result = await getattr(container_instance, method_name)(*args, **kwargs)
        result = base64.b64encode(msgpack.packb(result, default=encode_extras)).decode("utf-8")
        return Response(content=result, status_code=200)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            content={
                "exception_traceback": traceback.format_exc(),
                "exception_type": type(e).__name__,
                "exception_message": str(e),
            },
            status_code=580,
        )


sessions = {}
sessions_lock = threading.Lock()

def cleanup_session(session_id):
    with sessions_lock:
        session = sessions.pop(session_id, None)
    if session:
        session.terminate()

class Session:
    def __init__(self, session_id):
        self.session_id = session_id
        self.alive = True
        self.master_fd, self.slave_fd = pty.openpty()
        self.output_buffer = b""
        self.lock = threading.Lock()
        self.process = subprocess.Popen(
            [os.environ.get("SHELL", "/bin/bash")],
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            preexec_fn=os.setsid,
            close_fds=True,
        )
        self.read_thread = threading.Thread(target=self.read_from_process)
        self.read_thread.daemon = True
        self.read_thread.start()

    def read_from_process(self):
        while self.alive:
            try:
                if self.process.poll() is not None:
                    break
                rlist, _, _ = select.select([self.master_fd], [], [], 0.1)
                if self.master_fd in rlist:
                    data = os.read(self.master_fd, 1024)
                    if data:
                        with self.lock:
                            self.output_buffer += data
                    else:
                        # End of output, process might have exited
                        break
            except Exception as e:
                logging.error(f"Error in read_from_process: {e}")
                break
        self.alive = False
        cleanup_session(self.session_id)


    def write_to_process(self, data):
        if self.alive:
            try:
                os.write(self.master_fd, data)
            except OSError:
                # Handle the case where the file descriptor is invalid
                self.alive = False
        else:
            raise Exception("Process is not alive")

    def read_output(self):
        with self.lock:
            data = self.output_buffer
            self.output_buffer = b""
        return data

    def terminate(self):
        self.alive = False
        self.process.terminate()
        self.process.wait()  # Wait for the process to exit
        os.close(self.master_fd)
        os.close(self.slave_fd)


@app.post("/sessions")
def create_session():
    session_id = str(uuid.uuid4())
    session = Session(session_id)
    with sessions_lock:
        sessions[session_id] = session
    return {"session_id": session_id}

@app.post("/sessions/{session_id}/write")
async def send_input(session_id: str, request: Request):
    data = await request.json()
    with sessions_lock:
        session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.write_to_process(base64.b64decode(data["data"]))
    return {}

@app.post("/sessions/{session_id}/read")
def get_output(session_id: str):
    with sessions_lock:
        session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    output = session.read_output()
    return {"output": base64.b64encode(output).decode('utf-8')}


@app.post("/sessions/{session_id}/delete")
def delete_session(session_id: str):
    with sessions_lock:
        session = sessions.pop(session_id, None)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    session.terminate()
    return {}

if __name__ == "__main__":
    if platform.system() != "Darwin":
        subprocess.run(
            ["az", "login", "--identity",  "--allow-no-subscriptions"], check=True
        )  # if this fails, systemd will restart worker.py
    import uvicorn

    logging.basicConfig(level=logging.DEBUG)
    uvicorn.run(app, host="0.0.0.0", port=80)
