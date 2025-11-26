"""Main entry point for MCP Knowledge Graph Server."""
import uvicorn
from .config import config


def main():
    """Run the MCP server."""
    uvicorn.run(
        "src.api.server:app",
        host=config.host,
        port=config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()

