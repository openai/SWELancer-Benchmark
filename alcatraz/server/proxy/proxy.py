# fmt: off
# type: ignore
# ruff: noqa
# isort: skip_file
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import ConfigDict, BaseModel
import aiohttp
import uvicorn
import resource

# Each tcp connection uses a new file on the OS default limit of O(1K) is tiny.
resource.setrlimit(resource.RLIMIT_NOFILE, (131_072, 131_072))

app = FastAPI()
import logging
logging.basicConfig(level=logging.DEBUG)
@app.get("/health")
async def health():
    return "I'm a healthy proxy!"

class ProxyRequestBody(BaseModel):
    machine_info: str
    model_config = ConfigDict(extra="allow")

def new_session():
    # default aiohttp timeout is 5 minutes. We don't want any timeout, because
    # some proxied calls can be very long. It's up to the client to enforce a
    # client-side timeout.
    return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None))
@app.post("/proxy/{path:path}", status_code=200)
async def proxy_request(data: ProxyRequestBody, path: str):
    if data.machine_info.count('$') != 3:
        raise HTTPException(status_code=422, detail=f"machine_info not of valid form: {data.machine_info}")
    scaleset_name, _machine_id, ip, _machine_uuid = data.machine_info.split('$')
    print(ip, "is_generator", data.model_dump().get("is_generator", None))
    try:
        if data.model_dump().get("is_generator", None):
            session = await new_session().__aenter__()
            response = await session.post(f"http://{ip}/{path}", json=data.model_dump())
            async def content():
                async for data in response.content.iter_any():
                    yield data
                await session.__aexit__(None, None, None)
            return StreamingResponse(content=content(), status_code=response.status, media_type=response.content_type)
        else:
            async with new_session() as session:
                response = await session.post(f"http://{ip}/{path}", json=data.model_dump())
                response_data = await response.read()
                return Response(content=response_data, status_code=response.status, media_type=response.content_type)
    except aiohttp.ClientError as e:
        return Response(content=str(type(e))+str(e), status_code=503)
    except Exception as e:
        print(e)
        return Response(content=f"An unexpected error occurred: {str(type(e))+str(e)}", status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=90, timeout_keep_alive=10, log_config=None)
