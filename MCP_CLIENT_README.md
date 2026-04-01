# MCP Client for OpenCode - Python Terminal Interface

A Python script that lets you interact with OpenCode via terminal (no TUI) and automatically calls MCP tools based on your prompts.

---

## 📋 Prerequisites

1. **OpenCode installed** (CLI must be in PATH)
   ```bash
   opencode --version
   ```

2. **MCP Server configured** in `opencode.json` (e.g., `custom_test`)
   ```json
   {
     "mcp": {
       "custom_test": {
         "type": "local",
         "command": ["python3", "./custom_mcp/server.py"],
         "enabled": true
       }
     }
   }
   ```

3. **Python 3.8+**

---

## 🚀 Step-by-Step Usage

### Step 1: Install Prerequisites

```bash
# Make sure opencode is installed and in PATH
which opencode

# If not installed:
curl -fsSL https://opencode.ai/install | bash
# Then add to PATH:
export PATH="$HOME/.opencode/bin:$PATH"
```

### Step 2: Configure MCP Server

Ensure your `opencode.json` has an MCP server defined. Example:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "custom_test": {
      "type": "local",
      "command": ["python3", "./custom_mcp/server.py"],
      "enabled": true
    }
  }
}
```

> 💡 The `installation.sh` script already sets this up for you!

### Step 3: Run the Client

**Interactive Mode** (recommended for testing):
```bash
cd /path/to/opencode_mcp
python3 mcp_client.py
```

You'll see:
```
╔══════════════════════════════════════════════════════════════╗
║           OpenCode MCP Client - Terminal Interface           ║
╚══════════════════════════════════════════════════════════════╝

Type your prompts below. OpenCode will automatically use MCP tools.
Type 'exit', 'quit', or Ctrl+C to exit.
Type 'verbose' to toggle verbose JSON output.

Available MCP tools: custom_test (echo, add, multiply, greet, ...)
```

Then type prompts like:
```
>>> use custom_test echo to say hello world
```

**Single Prompt Mode** (for scripting):
```bash
python3 mcp_client.py "use custom_test add to calculate 5 + 7"
```

---

## 🧪 Example Session

```
>>> use custom_test echo to say hello

┌─ MCP Tools Called ──────────────────────────────────────────┐
│ 1. ✓ custom_test_echo
│    Input:  {"message": "hello"}
│    Output: Echo: hello
│
└──────────────────────────────────────────────────────────────┘

Assistant:
  The custom_test_echo tool returned: Echo: hello

>>> use custom_test add to calculate 42 + 8

┌─ MCP Tools Called ──────────────────────────────────────────┐
│ 1. ✓ custom_test_add
│    Input:  {"a": 42, "b": 8}
│    Output: 50
│
└──────────────────────────────────────────────────────────────┘

Assistant:
  The result is 50.

>>> exit
Goodbye!
```

---

## 🔍 How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  You type prompt in Python                                      │
│       ↓                                                         │
│  mcp_client.py runs:                                            │
│    opencode run --format json "your prompt"                     │
│       ↓                                                         │
│  OpenCode's LLM decides to use MCP tools                        │
│       ↓                                                         │
│  MCP Server (custom_test) executes the tool                     │
│       ↓                                                         │
│  JSON events streamed back:                                     │
│    { "type": "tool_use", "part": { "tool": "custom_test_add",   │
│                                    "state": { "input": {...},   │
│                                               "output": {...} } │
│    { "type": "text", "part": { "text": "The result is 50." } }  │
│       ↓                                                         │
│  mcp_client.py parses events → prints tools + response          │
└─────────────────────────────────────────────────────────────────┘
```

### Key CLI Flags Used

| Flag | Purpose |
|------|---------|
| `--format json` | Output raw JSON events (one per line) instead of formatted TUI |
| `run [message..]` | Run opencode headless with a single prompt |

### JSON Events Parsed

| Event Type | Contains |
|------------|----------|
| `tool_use` | `part.tool` (name), `part.state.input`, `part.state.output` |
| `text` | `part.text` (assistant's final response) |
| `error` | Error messages |

---

## 📁 Files

| File | Purpose |
|------|---------|
| `mcp_client.py` | The Python client script |
| `custom_mcp/server.py` | Your Python MCP server (provides tools) |
| `opencode.json` | Config linking MCP server to OpenCode |
| `installation.sh` | Full setup script |

---

## 🛠️ Troubleshooting

### "opencode command not found"
```bash
export PATH="$HOME/.opencode/bin:$PATH"
```

### "No MCP tools were called"
- Make sure your prompt explicitly asks for a tool, e.g., "use custom_test echo..."
- Check `opencode mcp list` to see if your MCP server is connected

### "Timeout"
- Increase the timeout in `mcp_client.py` (default: 120s)

### Verbose Mode
Type `verbose` in interactive mode to see raw JSON events:
```
>>> verbose
Verbose mode: ON
>>> test
→ Running: opencode run --format json test
→ Exit code: 0
  Event: tool_use
  Event: text
  ...
```

---

## 🎯 Quick Test

```bash
# 1. Setup everything
./installation.sh

# 2. Run client
python3 mcp_client.py "use custom_test greet to greet Bob"

# Expected output shows:
# - custom_test_greet tool called with {"name": "Bob"}
# - Output: "Hello, Bob! Welcome to OpenCode MCP testing."
```

---

Enjoy headless MCP testing! 🚀
