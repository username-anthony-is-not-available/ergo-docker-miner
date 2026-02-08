import socketio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
import subprocess
import logging
from typing import Dict, Any, Optional
import database
from miner_api import get_full_miner_data, get_gpu_names
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard")

# Global variable to store the latest miner data
miner_data: Dict[str, Any] = {
    'status': 'Starting...'
}

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    database.init_db()
    task = asyncio.create_task(background_task())
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)
sio_app = socketio.ASGIApp(sio, app)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

async def background_task() -> None:
    """Continuously fetches and broadcasts miner data."""
    while True:
        global miner_data
        try:
            # get_full_miner_data is synchronous, but we can run it in a thread to not block the event loop
            data = await asyncio.to_thread(get_full_miner_data)
            if data:
                miner_data = data
                await sio.emit('update', miner_data)
            else:
                miner_data['status'] = 'Error: Miner API unreachable'
                await sio.emit('update', miner_data)
        except Exception as e:
            logger.error(f"Error in background task: {e}")
            miner_data['status'] = f"Error: {str(e)}"
            await sio.emit('update', miner_data)

        await asyncio.sleep(5)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/config", response_class=HTMLResponse)
async def config(request: Request):
    return templates.TemplateResponse(request, "config.html")

def read_env_file() -> Dict[str, str]:
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key, value = parts
                        env_vars[key] = value
    return env_vars

def write_env_file(env_vars: Dict[str, str]) -> None:
    lines = []
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            lines = f.readlines()

    new_lines = []
    keys_written = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0]
            if key in env_vars:
                new_lines.append(f"{key}={env_vars[key]}\n")
                keys_written.add(key)
                continue
        new_lines.append(line)

    for key, value in env_vars.items():
        if key not in keys_written:
            new_lines.append(f"{key}={value}\n")

    with open('.env', 'w') as f:
        f.writelines(new_lines)

@app.get("/api/config")
async def get_config():
    return read_env_file()

@app.post("/api/config")
async def post_config(request: Request):
    data = await request.json()
    env_vars = read_env_file()
    for key, value in data.items():
        if value is True: value = 'true'
        if value is False: value = 'false'
        env_vars[key] = str(value)
    write_env_file(env_vars)
    return {"message": "Configuration saved successfully!"}

@app.post("/api/restart")
async def restart():
    try:
        # Run in thread to avoid blocking if it takes time
        await asyncio.to_thread(subprocess.run, ['./restart.sh'], check=True)
        return {"message": "Restarting..."}
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing restart script: {e}")
        return JSONResponse(status_code=500, content={"message": "Restart failed!"})

@app.get("/hashrate-history")
async def hashrate_history():
    history = await asyncio.to_thread(database.get_history)
    return history

@app.get("/api/logs")
async def get_logs():
    try:
        if os.path.exists('miner.log'):
            # Return last 100 lines
            import aiofiles
            async with aiofiles.open('miner.log', mode='r') as f:
                lines = await f.readlines()
                return {"logs": "".join(lines[-100:])}
        else:
            return {"logs": "Miner log file not found. Waiting for miner to start..."}
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/logs/download")
async def download_logs():
    if os.path.exists('miner.log'):
        return FileResponse('miner.log', filename='miner.log')
    else:
        return JSONResponse(status_code=404, content={"message": "Log file not found"})

@app.get("/api/gpu-models")
async def api_get_gpu_models():
    """Returns the detected GPU models."""
    try:
        models = await asyncio.to_thread(get_gpu_names)
        return {"models": models}
    except Exception as e:
        logger.error(f"Error fetching GPU models: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@sio.on('connect')
async def handle_connect(sid, environ):
    """Sends the initial data to the client upon connection."""
    if miner_data:
        await sio.emit('update', miner_data, to=sid)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("dashboard:sio_app", host='0.0.0.0', port=5000, reload=True)
