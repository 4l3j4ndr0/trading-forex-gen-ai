import { McpClient } from '@strands-agents/sdk'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'

/**
 * Crea un McpClient que conecta con el MCP server de TradingView.
 * Se pasa directamente como tool al agente — Strands se encarga de
 * listar los tools del MCP y exponerlos al LLM.
 */
export function createTradingViewMcpClient(): McpClient {
  const uvxPath = `${process.env.HOME}/.local/bin/uvx`

  return new McpClient({
    transport: new StdioClientTransport({
      command: uvxPath,
      args: ['--python', '3.13', '--from', 'tradingview-mcp-server', 'tradingview-mcp'],
    }),
  })
}
