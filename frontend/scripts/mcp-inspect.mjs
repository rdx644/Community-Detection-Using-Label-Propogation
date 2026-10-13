import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const configPath = process.argv[2] ?? 'C:/Users/putit/.codex/mcp/config.toml';
const config = await readFile(configPath, 'utf8');
const command = config.match(/^command\s*=\s*"([^"]+)"/m)?.[1];
const args = JSON.parse(config.match(/^args\s*=\s*(\[[^\n]+\])/m)?.[1] ?? '[]');
if (!command || !config.includes('[mcp_servers.shadcn]')) throw new Error('Expected shadcn stdio configuration');
const transport = new StdioClientTransport({ command, args, cwd: process.cwd(), env: process.env });
const client = new Client({ name: 'community-observatory', version: '1.0.0' });
try {
  await client.connect(transport);
  const { tools } = await client.listTools();
  const report = { timestamp: new Date().toISOString(), configPath, command, args, tools };
  const requested = process.argv[3];
  if (requested) {
    const tool = tools.find(tool => tool.name === requested);
    if (!tool) throw new Error(`Unknown MCP tool ${requested}`);
    const raw = process.argv[4]?.startsWith('@') ? await readFile(process.argv[4].slice(1), 'utf8') : (process.argv[4] ?? '{}');
    report.result = await client.callTool({ name: requested, arguments: JSON.parse(raw) });
  }
  const directory = path.resolve('../artifacts/verification');
  await mkdir(directory, { recursive: true });
  await writeFile(path.join(directory, requested ? `mcp-${requested}.json` : 'mcp-tools.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ timestamp: report.timestamp, tools: tools.map(tool => tool.name), result: report.result }, null, 2));
} finally {
  await client.close();
}
