#!/usr/bin/env python3
"""
Simple HTTP server for API Tester interface.
Serves the HTML interface and provides log endpoints.
"""
import os
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

app = FastAPI(title="API Tester Server")

# Get the directory where this script is located
BASE_DIR = Path(__file__).parent


@app.get("/")
async def serve_index():
    """Serve the main HTML interface."""
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/logs/{container_name}")
async def get_logs(container_name: str, lines: int = 100):
    """
    Fetch logs from a Docker container.
    
    Args:
        container_name: Name of the Docker container
        lines: Number of lines to fetch (default: 100)
    """
    try:
        # Use docker logs command to fetch logs
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return JSONResponse(
                status_code=404,
                content={"error": f"Container '{container_name}' not found or error: {result.stderr}"}
            )
        
        # Split logs into lines
        log_lines = result.stdout.strip().split('\n')
        
        return JSONResponse(content={
            "container": container_name,
            "logs": log_lines,
            "line_count": len(log_lines)
        })
    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=504,
            content={"error": "Timeout fetching logs"}
        )
    except FileNotFoundError:
        return JSONResponse(
            status_code=503,
            content={"error": "Docker command not found. Make sure Docker is installed and accessible."}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error fetching logs: {str(e)}"}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
