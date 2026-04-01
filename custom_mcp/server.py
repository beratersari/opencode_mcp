#!/usr/bin/env python3
"""
Custom MCP Server for OpenCode Testing

This is a sample MCP server demonstrating various tool types you can create.
It runs via stdio (stdin/stdout) and communicates using the MCP protocol.

Usage:
    python server.py

Requirements:
    pip install "mcp[cli]"
    # or: uv add "mcp[cli]"

Integration with OpenCode:
    Add to opencode.json:
    {
      "mcp": {
        "custom_test": {
          "type": "local",
          "command": ["python", "./custom_mcp/server.py"],
          "enabled": true
        }
      }
    }
"""

import sys
import logging
import math
from datetime import datetime
from typing import Optional

# Configure logging to stderr (NEVER print to stdout - it breaks MCP protocol)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Try to import MCP - provide helpful error if not installed
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: MCP SDK not installed.", file=sys.stderr)
    print("Install with: pip install 'mcp[cli]' or uv add 'mcp[cli]'", file=sys.stderr)
    sys.exit(1)

# Create the MCP server instance
mcp = FastMCP("CustomTestServer")

# =============================================================================
# TOOLS - These are callable by the LLM
# =============================================================================


@mcp.tool()
def echo(message: str) -> str:
    """
    Echo back the provided message. Simple test tool.

    Use this to verify the MCP server is working correctly.
    """
    logger.info(f"echo called with: {message}")
    return f"Echo: {message}"


@mcp.tool()
def add(a: int, b: int) -> int:
    """
    Add two integers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    """
    logger.info(f"add called: {a} + {b}")
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """
    Multiply two integers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b
    """
    logger.info(f"multiply called: {a} * {b}")
    return a * b


@mcp.tool()
def greet(name: str, title: Optional[str] = None) -> str:
    """
    Generate a greeting message.

    Args:
        name: The person's name to greet
        title: Optional title (e.g., 'Dr.', 'Mr.', 'Ms.')

    Returns:
        A friendly greeting string
    """
    logger.info(f"greet called: name={name}, title={title}")
    prefix = f"{title} " if title else ""
    return f"Hello, {prefix}{name}! Welcome to OpenCode MCP testing."


@mcp.tool()
def get_current_time(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Get the current date and time.

    Args:
        format: Python strftime format string (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        Current timestamp as formatted string
    """
    logger.info(f"get_current_time called with format: {format}")
    try:
        return datetime.now().strftime(format)
    except ValueError as e:
        return f"Error: Invalid format string - {e}"


@mcp.tool()
def reverse_text(text: str) -> str:
    """
    Reverse the given text string.

    Args:
        text: The text to reverse

    Returns:
        The reversed text
    """
    logger.info(f"reverse_text called")
    return text[::-1]


@mcp.tool()
def word_count(text: str) -> dict:
    """
    Count words, characters, and lines in text.

    Args:
        text: The text to analyze

    Returns:
        Dictionary with counts: words, chars, lines
    """
    logger.info(f"word_count called")
    words = len(text.split())
    chars = len(text)
    lines = len(text.splitlines())
    return {
        "words": words,
        "characters": chars,
        "lines": lines,
        "summary": f"{words} words, {chars} characters, {lines} lines"
    }


@mcp.tool()
def calculate(expression: str) -> str:
    """
    Safely evaluate a simple math expression.

    Supports: +, -, *, /, **, parentheses
    Example: "2 + 3 * (4 - 1)"

    Args:
        expression: Math expression as string

    Returns:
        The result or an error message
    """
    logger.info(f"calculate called: {expression}")
    try:
        # Safe eval with limited scope
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        allowed_names.update({"abs": abs, "round": round})
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_tools_info() -> str:
    """
    List all available tools in this MCP server with descriptions.

    Useful for discovering what this server can do.
    """
    logger.info("list_tools_info called")
    tools = [
        "echo(message) - Echo back a message",
        "add(a, b) - Add two integers",
        "multiply(a, b) - Multiply two integers",
        "greet(name, title?) - Generate greeting",
        "get_current_time(format?) - Get current timestamp",
        "reverse_text(text) - Reverse a string",
        "word_count(text) - Count words/chars/lines",
        "calculate(expression) - Evaluate math expression",
        "list_tools_info() - Show this list",
    ]
    return "Available tools:\n" + "\n".join(f"  • {t}" for t in tools)


# =============================================================================
# RESOURCES - These provide data that can be read
# =============================================================================


@mcp.resource("info://server")
def get_server_info() -> str:
    """Get information about this MCP server."""
    logger.info("Resource accessed: info://server")
    return """CustomTestServer MCP Server
Version: 1.0.0
Transport: stdio
Tools: 9
Purpose: Testing and demonstration for OpenCode
"""


@mcp.resource("time://now")
def get_time_resource() -> str:
    """Get current time as a resource."""
    logger.info("Resource accessed: time://now")
    return datetime.now().isoformat()


# =============================================================================
# PROMPTS - These are reusable prompt templates
# =============================================================================


@mcp.prompt()
def analyze_code(language: str, code: str) -> str:
    """
    Generate a prompt to analyze code.

    Args:
        language: Programming language (e.g., 'python', 'javascript')
        code: The code to analyze
    """
    return f"""Please analyze this {language} code:

```{language}
{code}
```

Focus on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Suggestions for improvement
"""


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting CustomTestServer MCP Server...")
    logger.info("Transport: stdio")
    logger.info("Ready to accept connections from OpenCode")

    # Run the MCP server over stdio
    mcp.run(transport="stdio")
