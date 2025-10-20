import express from 'express';
import { atxpExpress, requirePayment, ATXPPaymentDestination } from '@atxp/express';
import BigNumber from 'bignumber.js';
import fetch from 'node-fetch';
import dotenv from 'dotenv';

dotenv.config();

// Configuration
const RAG_BASE_URL = 'http://localhost:8000';
const RAG_ASK_ENDPOINT = `${RAG_BASE_URL}/ask/`;
const ATXP_CONNECTION = process.env.ATXP_CONNECTION_STRING;

if (!ATXP_CONNECTION) {
  console.error('❌ ATXP_CONNECTION_STRING not set');
  process.exit(1);
}

// Express app
const app = express();
app.use(express.json());

// OAuth metadata endpoint (MUST come before atxpExpress middleware)
app.get('/.well-known/oauth-authorization-server', (req, res) => {
  console.log('📡 OAuth metadata requested');
  res.json({
    issuer: 'https://97d2858bdad6.ngrok-free.app',
    authorization_endpoint: 'https://97d2858bdad6.ngrok-free.app/oauth/authorize',
    token_endpoint: 'https://97d2858bdad6.ngrok-free.app/oauth/token'
  });
});

// Add ATXP payment middleware
app.use(atxpExpress({
  paymentDestination: new ATXPPaymentDestination(ATXP_CONNECTION),
  payeeName: 'Interview RAG Server',
  allowHttp: true
}));

// MCP endpoint - handle requests manually with JSON-RPC 2.0
app.post('/', async (req, res) => {
  console.log('📥 MCP request received:', JSON.stringify(req.body, null, 2));
  
  try {
    const { method, params, id } = req.body;
    
    if (method === 'initialize') {
      console.log('🤝 Handling initialize handshake');
      res.json({
        jsonrpc: '2.0',
        id: id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: {}
          },
          serverInfo: {
            name: 'interview-rag-server',
            version: '1.0.0'
          }
        }
      });
    } else if (method === 'notifications/initialized') {
      // Just acknowledge, no response needed for notifications
      console.log('✅ Client initialized');
      res.status(200).end();
    } else if (method === 'tools/list') {
      console.log('📋 Listing tools');
      res.json({
        jsonrpc: '2.0',
        id: id,
        result: {
          tools: [
            {
              name: 'ask_rag',
              description: 'Ask questions about uploaded documents',
              inputSchema: {
                type: 'object',
                properties: {
                  question: { type: 'string', description: 'Your question' },
                  mode: {
                    type: 'string',
                    enum: ['auto', 'qa', 'summary'],
                    description: 'Answer mode',
                    default: 'auto'
                  }
                },
                required: ['question']
              }
            }
          ]
        }
      });
    } else if (method === 'tools/call') {
      const { name, arguments: args } = params;
      
      if (name === 'ask_rag') {
        const { question, mode = 'auto' } = args;
        
        const prices = {
          qa: new BigNumber('0.01'),
          summary: new BigNumber('0.05'),
          auto: new BigNumber('0.05')
        };
        
        console.log(`💰 Requiring payment: $${prices[mode]}`);
        
        try {
          // ✅ FIXED: Call requirePayment WITHOUT req parameter
          await requirePayment({ price: prices[mode] });
          console.log('✅ Payment validated!');
        } catch (paymentError) {
          console.error('❌ Payment error:', paymentError);
          return res.json({
            jsonrpc: '2.0',
            id: id,
            error: { 
              code: -32603, 
              message: `Payment failed: ${paymentError.message}` 
            }
          });
        }
        
        console.log(`🔄 Calling RAG backend with question: "${question}"`);
        const response = await fetch(RAG_ASK_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, mode })
        });
        
        if (!response.ok) {
          throw new Error(`RAG backend returned ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ RAG response received');
        
        res.json({
          jsonrpc: '2.0',
          id: id,
          result: {
            content: [{
              type: 'text',
              text: `Question: ${question}\nMode: ${data.mode}\n\nAnswer:\n${data.answer}`
            }]
          }
        });
      } else {
        res.json({
          jsonrpc: '2.0',
          id: id,
          error: { code: -32601, message: `Unknown tool: ${name}` }
        });
      }
    } else {
      res.json({
        jsonrpc: '2.0',
        id: id,
        error: { code: -32601, message: `Unknown method: ${method}` }
      });
    }
  } catch (error) {
    console.error('❌ MCP error:', error);
    res.json({
      jsonrpc: '2.0',
      id: req.body.id,
      error: { code: -32603, message: error.message }
    });
  }
});

app.listen(8001, () => {
  console.log('🚀 Interview RAG MCP Server running on http://localhost:8001');
  console.log('📡 Exposed via ngrok: https://97d2858bdad6.ngrok-free.app');
  console.log('📡 RAG Backend: ' + RAG_BASE_URL);
  console.log('✅ Ready for ATXP payments (JSON-RPC 2.0)');
});