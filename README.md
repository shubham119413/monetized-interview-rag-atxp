# Monetized Multi-Modal RAG with ATXP

Full-stack RAG system with ATXP payment integration for monetizing AI tools.

## Architecture

- **Agent**: Node.js ATXP client (pays for tools)
- **MCP Server**: Node.js + ATXP Express (validates payments)
- **RAG Backend**: Python FastAPI + FAISS + Gemini
- **Pricing**: $0.01 (QA), $0.05 (Summary)

## Setup

See individual folders for setup instructions:
- `/interview-rag` - Python RAG backend
- `/mcp-server` - Node.js MCP server with ATXP
- `/atxp-agent` - Node.js ATXP agent client

## Running Locally

Requires 4 terminals + ngrok for HTTPS tunneling.
