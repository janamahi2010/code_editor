import asyncio

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# One entry per deployed backend instance. Each instance only runs one
# sandboxed script at a time (see backend/app/main.py's blocking /run
# handler), so having N instances lets N scripts run concurrently.
BACKEND_URLS = [
    "https://code-editor-gyks.onrender.com",
    "https://code-editor-1-pxvj.onrender.com",
    "https://code-editor-2-m20h.onrender.com",
    "https://code-editor-3-vsb7.onrender.com",
    "https://code-editor-4-5btg.onrender.com",
    "https://code-editor-5-4dpi.onrender.com",
    "https://code-editor-6-fiy0.onrender.com",
    "https://code-editor-7.onrender.com",
    "https://code-editor-8.onrender.com",
    "https://code-editor-9.onrender.com",
]

# Generous ceiling covering Render free-tier cold start (up to ~60s) plus
# the backend's own 60s sandbox execution timeout (see backend/app/executor.py).
REQUEST_TIMEOUT_SECONDS = 150.0

app = FastAPI(title="QuantumSIA Dispatcher")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Free-worker pool: get() blocks until a backend is available, put() returns
# it. This is what gives "3rd request reuses the 1st backend once it's free"
# behavior, instead of blind round-robin.
free_backends: asyncio.Queue = asyncio.Queue()


@app.on_event("startup")
async def seed_pool():
    for url in BACKEND_URLS:
        free_backends.put_nowait(url)


class RunRequest(BaseModel):
    code: str


@app.post("/run")
async def run_code(request: RunRequest):
    backend_url = await free_backends.get()
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{backend_url}/run", json={"code": request.code})
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Backend {backend_url} unreachable: {e}")
    finally:
        await free_backends.put(backend_url)


@app.get("/pool-status")
async def pool_status():
    return {"total": len(BACKEND_URLS), "free": free_backends.qsize()}
