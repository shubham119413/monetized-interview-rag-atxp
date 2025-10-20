# Complete Setup Guide - Monetized RAG with ATXP

This guide will walk you through setting up the full ATXP-integrated RAG system from scratch.

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **ngrok account** (free tier works)
- **ATXP account** with funds

---

## Architecture Overview

```
┌─────────────────┐
│ ATXP Agent      │  (Node.js - pays for tools)
│ (atxp-agent/)   │
└────────┬────────┘
         │ HTTPS via ngrok
         ↓
┌─────────────────┐
│ MCP Server      │  (Node.js - validates payments)
│ (mcp-server/)   │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│ RAG Backend     │  (Python - original RAG)
│ (interview-rag/)│
└─────────────────┘
```

---

## Part 1: Set Up Original RAG Backend

### 1.1 Clone the Original RAG

```bash
git clone https://github.com/shubham119413/interview-rag.git
cd interview-rag
```

### 1.2 Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 1.3 Install Dependencies

```bash
pip install -r requirements.txt
```

### 1.4 Configure Environment

Create `.env` file:
```bash
touch .env
```

Add your Gemini API key:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your key from: https://aistudio.google.com/app/apikey

### 1.5 Start the RAG Backend

```bash
uvicorn main:app --reload --port 8000
```

**Verify:** Visit http://localhost:8000 - should see `{"message":"Hello from FastAPI 🎉"}`

### 1.6 Upload Sample Data

Open a new terminal:
```bash
cd interview-rag
streamlit run app.py
```

Upload a PDF, audio, or video file through the UI. Wait for processing to complete.

**Keep this terminal running.**

---

## Part 2: Set Up MCP Server (Node.js)

### 2.1 Navigate to MCP Server

```bash
cd ../monetized-interview-rag-atxp/mcp-server
```

### 2.2 Install Dependencies

```bash
npm install
```

This installs:
- `express`
- `@atxp/express`
- `bignumber.js`
- `node-fetch`
- `dotenv`

### 2.3 Configure Environment

Create `.env` file:
```bash
touch .env
```

Add your ATXP connection string:
```
ATXP_CONNECTION_STRING=https://accounts.atxp.ai?connection_token=YOUR_TOKEN&account_id=YOUR_ACCOUNT_ID
```

Get this from: https://accounts.atxp.ai

### 2.4 Set Up ngrok

Install ngrok:
```bash
brew install ngrok  # macOS
# OR download from https://ngrok.com/download
```

Sign up and get authtoken:
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

Get authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken

### 2.5 Start MCP Server

**Terminal 2:**
```bash
node mcp_server_node.js
```

Should see:
```
🚀 Interview RAG MCP Server running on http://localhost:8001
```

### 2.6 Expose via ngrok

**Terminal 3:**
```bash
ngrok http 8001
```

Copy the `https://` URL (e.g., `https://abc123.ngrok-free.app`)

**Keep both terminals running.**

---

## Part 3: Set Up ATXP Agent (Node.js)

### 3.1 Navigate to Agent Folder

```bash
cd ../atxp-agent
```

### 3.2 Install Dependencies

```bash
npm install
```

This installs:
- `@atxp/client`
- `dotenv`
- `typescript`
- `ts-node`
- `@types/node`

### 3.3 Configure Environment

Create `.env` file:
```bash
touch .env
```

Add:
```
ATXP_CONNECTION_STRING=https://accounts.atxp.ai?connection_token=YOUR_TOKEN&account_id=YOUR_ACCOUNT_ID
```

(Same as MCP server)

### 3.4 Update Agent with ngrok URL

Edit `agent.ts` and replace the `mcpServer` URL:

```typescript
const askRagService = {
  mcpServer: 'https://YOUR_NGROK_URL_HERE',  // Paste your ngrok URL
  toolName: 'ask_rag',
  // ... rest stays the same
};
```

### 3.5 Verify MCP Server OAuth Metadata

Edit `mcp_server_node.js` and update the OAuth metadata endpoint with your ngrok URL:

```javascript
app.get('/.well-known/oauth-authorization-server', (req, res) => {
  res.json({
    issuer: 'https://YOUR_NGROK_URL',  // Update this
    authorization_endpoint: 'https://YOUR_NGROK_URL/oauth/authorize',
    token_endpoint: 'https://YOUR_NGROK_URL/oauth/token'
  });
});
```

Restart the MCP server after this change.

---

## Part 4: Run the Full System

You should now have **4 terminals** running:

**Terminal 1:** FastAPI RAG Backend
```
INFO: Uvicorn running on http://127.0.0.1:8000
```

**Terminal 2:** MCP Server
```
🚀 Interview RAG MCP Server running on http://localhost:8001
```

**Terminal 3:** ngrok
```
Forwarding    https://abc123.ngrok-free.app -> http://localhost:8001
```

**Terminal 4:** Ready for ATXP Agent

---

## Part 5: Test the System

### 5.1 Run the Agent

```bash
cd atxp-agent
npx ts-node agent.ts
```

### 5.2 Authorize Payment

The agent will output a payment URL:
```
Payment via ATXP is required. Please pay at: https://auth.atxp.ai/payment-request/...
```

1. Open that URL in your browser
2. Review the payment ($0.05)
3. Click "Authorize"
4. Complete the payment

### 5.3 Run Agent Again

```bash
npx ts-node agent.ts
```

**Expected output:**
```
✅ ATXP client connected
🔧 Testing ask_rag tool...
✅ Ask questions about documents result successful!
Result: {
  content: [ { type: 'text', text: '...' } ]
}
```

---

## Pricing Structure

| Tool | Mode | Price |
|------|------|-------|
| `ask_rag` | QA (concise) | $0.01 |
| `ask_rag` | Summary (detailed) | $0.05 |
| `ask_rag` | Auto | $0.05 |

---

## Troubleshooting

### Error: "No embeddings found"

**Solution:** Upload documents to the RAG first via Streamlit UI or:
```bash
curl -X POST http://localhost:8000/upload/ -F "file=@yourfile.pdf"
```

### Error: "ATXP_CONNECTION_STRING not set"

**Solution:** Make sure `.env` files exist in both `mcp-server/` and `atxp-agent/` with valid connection strings.

### Error: "only requests to HTTPS are allowed"

**Solution:** You need ngrok. Make sure:
1. ngrok is running on port 8001
2. Agent's `agent.ts` uses the ngrok HTTPS URL
3. MCP server's OAuth metadata uses ngrok URL

### Error: "RAG backend returned 400"

**Solution:** Either:
1. RAG has no documents (upload via Streamlit)
2. RAG is not running (check Terminal 1)

### Payment authorization required every time

**This is expected.** Each session requires payment authorization. This is ATXP's security model.

---

## Development Workflow

### Making Changes to MCP Server

1. Edit `mcp_server_node.js`
2. Restart: Ctrl+C, then `node mcp_server_node.js`
3. ngrok URL stays the same (no agent changes needed)

### Making Changes to Agent

1. Edit `agent.ts`
2. Run: `npx ts-node agent.ts`

### If ngrok URL changes

1. Update `agent.ts` with new URL
2. Update `mcp_server_node.js` OAuth metadata
3. Restart MCP server

---

## Project Structure

```
monetized-interview-rag-atxp/
├── mcp-server/              # Node.js MCP server
│   ├── mcp_server_node.js   # Main server file
│   ├── package.json
│   ├── .env                 # Your secrets (git-ignored)
│   └── .env.example         # Template
├── atxp-agent/              # Node.js ATXP client
│   ├── agent.ts             # Agent code
│   ├── package.json
│   ├── tsconfig.json
│   ├── .env                 # Your secrets (git-ignored)
│   └── .env.example         # Template
└── README.md

interview-rag/               # Original Python RAG (separate repo)
├── main.py                  # FastAPI backend
├── app.py                   # Streamlit frontend
├── requirements.txt
└── .env                     # Gemini API key
```

---

## Next Steps

1. **Add more tools**: Implement `upload_file` tool with size-based pricing
2. **Improve error handling**: Better payment failure messages
3. **Add logging**: Track payment transactions
4. **Deploy**: Use a permanent domain instead of ngrok

---

## Resources

- **Original RAG**: https://github.com/shubham119413/interview-rag
- **ATXP Docs**: https://docs.atxp.ai
- **ATXP Account**: https://accounts.atxp.ai
- **ngrok**: https://ngrok.com

---

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review ATXP docs
3. Open an issue on GitHub

---

**Congratulations!** You now have a fully functional monetized RAG system with ATXP payment integration. 🎉