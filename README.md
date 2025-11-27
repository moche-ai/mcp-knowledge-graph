# MCP Knowledge Graph

A **Model Context Protocol (MCP)** server that provides verified knowledge with trust scores, reasoning capabilities, and fact-checking.

> 🌐 **Live Server**: https://mcp.moche.ai

## Why Use This?

Unlike simple document search (like Context7), this MCP server provides:

| Feature | Simple Search | MCP Knowledge Graph |
|---------|--------------|---------------------|
| Document lookup | ✅ | ✅ |
| **Trust scores** | ❌ | ✅ Verified information |
| **Relationships** | ❌ | ✅ Dependencies, alternatives |
| **Reasoning** | ❌ | ✅ "Why" and "How" answers |
| **Best practices** | ❌ | ✅ Pitfalls and recommendations |

## Quick Start

### Use the Public Server

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "knowledge-graph": {
      "transport": {
        "type": "sse",
        "url": "https://mcp.moche.ai/mcp/sse"
      }
    }
  }
}
```

### Self-Host with Docker

```bash
# Clone the repository
git clone https://github.com/moche-ai/mcp-knowledge-graph.git
cd mcp-knowledge-graph

# Set environment variables
export NEO4J_PASSWORD=your_password

# Run with Docker Compose
docker compose up -d
```

### Install from Source

```bash
pip install mcp-knowledge-graph

# Or install from source
pip install -e .

# Run the server
mcp-kg-server
```

## Available Tools

| Tool | Description |
|------|-------------|
| `search_knowledge` | Search for verified information with trust scores |
| `get_context` | Get complete context: dependencies, alternatives, integrations |
| `get_dependencies` | Get dependency chain for installation order |
| `get_alternatives` | Find alternative technologies/tools |
| `get_best_practices` | Get recommendations and pitfall warnings |
| `get_stats` | Get knowledge graph statistics |
| `infer_relation` | Infer relationships between two technologies |
| `find_path` | Find connection paths between concepts |
| `recommend` | Get technology recommendations (similar, alternative, complement) |
| `find_similar` | Find similar technologies by category/tags |

## Usage Examples

### Search Knowledge

```bash
curl -X POST https://mcp.moche.ai/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_knowledge",
    "arguments": {"query": "vector database", "min_trust": 0.8}
  }'
```

### Get Context

```bash
curl https://mcp.moche.ai/knowledge/context/langchain
```

### Get Dependencies

```bash
curl -X POST https://mcp.moche.ai/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_dependencies",
    "arguments": {"name": "langgraph", "max_depth": 3}
  }'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp/info` | GET | MCP server info |
| `/mcp/tools/list` | GET | List available tools |
| `/mcp/tools/call` | POST | Call a tool |
| `/mcp/resources/list` | GET | List resources |
| `/mcp/resources/read` | POST | Read a resource |
| `/mcp/sse` | GET | SSE streaming endpoint |
| `/knowledge/search` | GET | REST search endpoint |
| `/knowledge/context/{name}` | GET | REST context endpoint |
| `/knowledge/stats` | GET | Graph statistics |
| `/knowledge/infer/relation` | GET | Infer relations between technologies |
| `/knowledge/infer/path` | GET | Find paths between concepts |
| `/knowledge/recommend/{name}` | GET | Get recommendations |
| `/knowledge/similar/{name}` | GET | Find similar technologies |
| `/knowledge/viewer` | GET | 3D Knowledge Graph Viewer |
| `/docs` | GET | OpenAPI documentation |

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MCP_PORT` | 8780 | Server port |
| `NEO4J_URI` | bolt://localhost:7687 | Neo4j connection URI |
| `NEO4J_USER` | neo4j | Neo4j username |
| `NEO4J_PASSWORD` | - | Neo4j password (required) |
| `MIN_TRUST_SCORE` | 0.7 | Default minimum trust score |

## Trust Scores

All information has a trust score (0-1):

| Level | Score | Meaning |
|-------|-------|---------|
| Verified | 0.9-1.0 | From official sources (GitHub, official docs) |
| High | 0.7-0.9 | From trusted sources (ArXiv, reputable blogs) |
| Medium | 0.5-0.7 | Community-verified |
| Low | 0.3-0.5 | Single source, unverified |
| Unverified | 0.0-0.3 | Needs verification |

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

If you find this project helpful, consider supporting its development:

- ⭐ Star this repository
- 🐛 Report issues or suggest features
- 💬 Share with others

`ETH: 0x0000C4CE7f73886Cce8C43d4b481f0cBEbAC0000`

## Links

- 🌐 **Live Server**: https://mcp.moche.ai
- 🧠 **Knowledge Graph Viewer**: https://mcp.moche.ai/knowledge/viewer
- 📖 **API Docs**: https://mcp.moche.ai/docs
- 🔗 **GitHub**: https://github.com/moche-ai/mcp-knowledge-graph

---

Made with ❤️ by [MOCHE.AI](https://moche.ai)

