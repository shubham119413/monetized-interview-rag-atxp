import dotenv from 'dotenv';
import { atxpClient, ATXPAccount } from '@atxp/client';

// Load environment variables
dotenv.config();

// Define your RAG MCP service
const askRagService = {
  mcpServer: 'https://97d2858bdad6.ngrok-free.app',
  toolName: 'ask_rag',
  description: 'Ask questions about documents',
  getArguments: (question: string) => ({ question, mode: 'auto' }),
  getResult: (result: any) => result
};

// Main function
async function main() {
  console.log('🚀 Starting ATXP Agent...');
  
  // Get connection string
  const connectionString = process.env.ATXP_CONNECTION_STRING;
  
  if (!connectionString) {
    console.error('❌ ATXP_CONNECTION_STRING not found in .env');
    process.exit(1);
  }
  
  console.log('✅ Connection string loaded');
  
  // Create ATXP client
  console.log('🔌 Connecting to MCP server...');
  const client = await atxpClient({
    mcpServer: askRagService.mcpServer,
    account: new ATXPAccount(connectionString),
  });
  
  console.log('✅ ATXP client connected');
  
  // Try calling a tool
  console.log('🔧 Testing ask_rag tool...');
  
  const prompt = 'What is the structure followed by the speaker?';
  
  try {
    const result = await client.callTool({
      name: askRagService.toolName,
      arguments: askRagService.getArguments(prompt),
    });
    
    console.log(`✅ ${askRagService.description} result successful!`);
    console.log('Result:', askRagService.getResult(result));
  } catch (error) {
    console.error(`❌ Error with ${askRagService.description}:`, error);
    process.exit(1);
  }
}

main().catch(error => {
  console.error('❌ Fatal error:', error);
  process.exit(1);
});