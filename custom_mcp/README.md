# Custom MCP Server for OpenCode

A sample MCP (Model Context Protocol) server built with Python for testing with OpenCode.

## What is This?

This is a **local MCP server** that runs as a Python subprocess and communicates with OpenCode via **stdio** (stdin/stdout). It provides example tools you can call from the LLM.

## Features

### Tools (Callable by LLM)

| Tool | Description |
|------|-------------|
| `echo(message)` | Echo back a message (great for testing) |
| `add(a, b)` | Add two integers |
| `multiply(a, b)` | Multiply two integers |
| `greet(name, title?)` | Generate a friendly greeting |
| `get_current_time(format?)` | Get current date/time |
| `reverse_text(text)` | Reverse a string |
| `word_count(text)` | Count words, chars, lines |
| `calculate(expression)` | Evaluate simple math expressions |
| `list_tools_info()` | List all available tools |

### Resources (Readable Data)

| Resource | Description |
|----------|-------------|
| `info://server` | Server info |
| `time://now` | Current ISO timestamp |

### Prompts (Reusable Templates)

| Prompt | Description |
|--------|-------------|
| `analyze_code(language, code)` | Generate code analysis prompt |

## Setup

### 1. Install Python MCP SDK

```bash
# Using pip
pip install "mcp[cli]"

# Or using uv (recommended)
uv add "mcp[cli]"
```

Requires Python 3.10+.

### 2. Test the Server (Optional)

```bash
cd /testbed/opencode_mcp/custom_mcp
python server.py
```

If it starts without errors, it's working. Press Ctrl+C to stop.

You can also test with MCP CLI:
```bash
mcp dev server.py
```

### 3. Configure OpenCode

Add to your `opencode.json` (in project root or `~/.config/opencode/`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "custom_test": {
      "type": "local",
      "command": ["python", "./custom_mcp/server.py"],
      "enabled": true
    }
  }
}
```

> **Note:** Use the full path if running from a different directory:
> `"command": ["python", "/absolute/path/to/custom_mcp/server.py"]`

### 4. Use It!

Start OpenCode and prompt the LLM:

```
Use the custom_test echo tool to say hello
Use custom_test add to calculate 5 + 7
```

Or reference it in your `AGENTS.md`:

```markdown
When you need to test MCP integration, use the custom_test tools.
```

## How It Works

```
┌─────────────┐         stdio          ┌──────────────┐
│   OpenCode  │◄─────────────────────►│  Python MCP  │
│   (TUI)     │   JSON-RPC over stdio  │  Server      │
└─────────────┘                        └──────────────┘
```

1. OpenCode spawns `python server.py` as a child process
2. They communicate via **stdin/stdout** using MCP JSON-RPC
3. Tools defined with `@mcp.tool()` become available to the LLM
4. **Never print to stdout** — it corrupts the protocol (use stderr for logs)

## Troubleshooting

### "MCP SDK not installed"
```bash
pip install "mcp[cli]"
```

### Server fails to connect
- Check the command path in `opencode.json` is correct
- Run `python server.py` manually to see errors (stderr)

### Tools not appearing
- Restart OpenCode after changing config
- Check `opencode mcp list` for server status

### Logging
All logs go to **stderr**. Check OpenCode's output or run the server manually to see them.

## Customization

Edit `server.py` to add your own tools:

```python
@mcp.tool()
def my_custom_tool(param: str) -> str:
    """Description shown to LLM."""
    return f"Result: {param.upper()}"
```

## License

MIT — feel free to use and modify for your projects!
