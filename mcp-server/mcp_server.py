"""
HTTP-based MCP Server that wraps the Interview RAG FastAPI backend.
Exposes /ask/ and /upload/ endpoints as MCP tools via HTTP.

Pricing:
  - ask_rag (QA mode): $0.01
  - ask_rag (Summary mode): $0.05
  - upload_file: FREE (<100MB), $0.05 (100MB+)

Run with: python mcp_server.py
Accessible at: http://localhost:8001
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from typing import Any, Dict, List
import uvicorn

# Create FastAPI app for MCP server
app = FastAPI(title="Interview RAG MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAG backend URL
RAG_BASE_URL = "http://localhost:8000"
RAG_ASK_ENDPOINT = f"{RAG_BASE_URL}/ask/"
RAG_UPLOAD_ENDPOINT = f"{RAG_BASE_URL}/upload_async/"

# HTTP client
http_client = httpx.AsyncClient(timeout=300.0)

# Upload pricing
UPLOAD_THRESHOLD_MB = 100
UPLOAD_PRICE_LARGE = 0.05

def calculate_upload_cost(file_size_bytes: int) -> float:
    """Calculate upload cost: FREE if <100MB, $0.05 if 100MB+"""
    size_mb = file_size_bytes / (1024 * 1024)
    return UPLOAD_PRICE_LARGE if size_mb >= UPLOAD_THRESHOLD_MB else 0.00

# =========================
# MCP Tool Definitions (as data)
# =========================

TOOLS = {
    "ask_rag": {
        "name": "ask_rag",
        "description": "Ask a question about the uploaded documents. Uses RAG to retrieve context and Gemini to generate an answer. Pricing: $0.01 (QA), $0.05 (Summary).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Your question about the documents"
                },
                "mode": {
                    "type": "string",
                    "enum": ["auto", "qa", "summary"],
                    "description": "Answer mode: auto (intelligent), qa (concise, $0.01), or summary (detailed, $0.05)",
                    "default": "auto"
                }
            },
            "required": ["question"]
        }
    },
    "upload_file": {
        "name": "upload_file",
        "description": "Upload a file to the RAG system for processing. Pricing: FREE (<100MB), $0.05 (100MB+). Supports: PDF, MP3, WAV, MP4, MOV.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Local path to the file to upload (e.g., /path/to/interview.pdf)"
                }
            },
            "required": ["file_path"]
        }
    }
}

# =========================
# Request/Response Models
# =========================

class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

class ToolResponse(BaseModel):
    content: List[Dict[str, str]]

# =========================
# Endpoints
# =========================

@app.get("/")
def root():
    return {
        "message": "Interview RAG MCP Server",
        "tools": list(TOOLS.keys()),
        "rag_backend": RAG_BASE_URL
    }

@app.get("/tools")
def list_tools():
    """List available MCP tools"""
    return {"tools": list(TOOLS.values())}

@app.post("/call-tool", response_model=ToolResponse)
async def call_tool(request: ToolCallRequest):
    """Execute an MCP tool"""
    tool_name = request.name
    args = request.arguments
    
    try:
        if tool_name == "ask_rag":
            result = await handle_ask(args)
        elif tool_name == "upload_file":
            result = await handle_upload(args)
        else:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        return {"content": [{"type": "text", "text": result}]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Tool Handlers
# =========================

async def handle_ask(args: dict) -> str:
    """Call RAG /ask/ endpoint"""
    question = args.get("question", "")
    mode = args.get("mode", "auto")
    
    if not question:
        return "Error: 'question' is required"
    
    payload = {"question": question, "mode": mode}
    resp = await http_client.post(RAG_ASK_ENDPOINT, json=payload)
    
    if resp.status_code != 200:
        return f"RAG ask failed: {resp.status_code} - {resp.text}"
    
    data = resp.json()
    
    # Format response
    formatted = f"Question: {question}\n"
    formatted += f"Mode: {data.get('mode', 'unknown')}\n\n"
    formatted += f"Answer:\n{data.get('answer', '')}\n\n"
    
    chunks = data.get("retrieved_chunks", [])
    if chunks:
        formatted += f"--- Retrieved {len(chunks)} chunks for context ---\n"
        for i, ch in enumerate(chunks[:3], 1):
            formatted += f"\n{i}. {ch.get('source', 'unknown')} (chunk {ch.get('chunk_id', '?')})\n"
    
    return formatted

async def handle_upload(args: dict) -> str:
    """Upload file to RAG"""
    file_path = args.get("file_path", "")
    
    if not file_path:
        return "Error: 'file_path' is required"
    
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    
    # Get file size and calculate cost
    file_size = os.path.getsize(file_path)
    cost = calculate_upload_cost(file_size)
    size_mb = file_size / (1024 * 1024)
    
    # Read file
    with open(file_path, "rb") as f:
        file_data = f.read()
    
    filename = os.path.basename(file_path)
    
    # Upload to RAG
    files = {"file": (filename, file_data, "application/octet-stream")}
    resp = await http_client.post(RAG_UPLOAD_ENDPOINT, files=files)
    
    if resp.status_code != 200:
        return f"Upload failed: {resp.status_code} - {resp.text}"
    
    data = resp.json()
    
    # Format response
    formatted = f"✅ File uploaded successfully!\n\n"
    formatted += f"📁 File: {filename}\n"
    formatted += f"📊 Size: {size_mb:.2f} MB\n"
    formatted += f"💰 Cost: ${cost:.2f}\n"
    formatted += f"📍 Job ID: {data.get('job_id', 'unknown')}\n\n"
    formatted += f"Status: {data.get('message', 'Processing...')}"
    
    return formatted

# =========================
# Startup
# =========================

if __name__ == "__main__":
    print("🚀 Starting Interview RAG MCP Server (HTTP)...")
    print(f"📡 RAG Backend: {RAG_BASE_URL}")
    print("📋 Available tools:")
    print("   - ask_rag: Ask questions with RAG + Gemini")
    print("       • QA mode: $0.01")
    print("       • Summary mode: $0.05")
    print("   - upload_file: Upload files")
    print("       • <100 MB: FREE")
    print("       • 100+ MB: $0.05")
    print("\n✅ Server starting on http://localhost:8001")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)