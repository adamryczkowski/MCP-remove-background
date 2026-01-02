"""CLI entry point for Background Removal MCP Server."""

import click

from MCP_remove_background.server import mcp


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Background Removal MCP Server CLI.

    If no command is specified, runs the server with default stdio transport.
    """
    if ctx.invoked_subcommand is None:
        # Default behavior: run serve with stdio transport
        ctx.invoke(serve)


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http", "http"]),
    default="stdio",
    help="Transport protocol for the MCP server.",
)
@click.option(
    "--port",
    type=int,
    default=8083,
    help="Port for HTTP/SSE transport.",
)
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Host for HTTP/SSE transport.",
)
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error"]),
    default="info",
    help="Log level for the server.",
)
def serve(transport: str, port: int, host: str, log_level: str) -> None:
    """Start the MCP server.

    By default, uses stdio transport for compatibility with VS Code MCP clients.
    Use --transport streamable-http for shared server mode to reduce CPU usage
    when running multiple VS Code windows.

    Examples:
        mcp-remove-background serve                           # stdio transport (default)
        mcp-remove-background serve --transport streamable-http  # HTTP transport on port 8083
        mcp-remove-background serve --transport streamable-http --port 9000  # Custom port
    """
    if transport == "stdio":
        mcp.run()
    elif transport == "sse":
        mcp.run(transport="sse", host=host, port=port, log_level=log_level)
    elif transport in ("streamable-http", "http"):
        mcp.run(transport="streamable-http", host=host, port=port, log_level=log_level)


def main() -> None:
    """Run the Background Removal MCP server."""
    cli()


if __name__ == "__main__":
    main()
