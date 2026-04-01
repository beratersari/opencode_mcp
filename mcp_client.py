#!/usr/bin/env python3
"""
MCP Client for OpenCode - Headless Terminal Interface

This script lets you interact with OpenCode via Python terminal (no TUI).
It sends your prompts to opencode CLI, which uses MCP tools automatically,
and returns the called tools and their responses.

Usage:
    python3 mcp_client.py

Then type your prompts at the >>> prompt.

Example prompts:
    - "use custom_test echo to say hello"
    - "use custom_test add to calculate 5 + 7"
    - "greet Alice using custom_test"
    - "what time is it using custom_test get_current_time"
"""

import subprocess
import json
import sys
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def http_post(url: str, data: dict) -> dict:
    """Simple HTTP POST returning JSON."""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_via_api(base_url: str, session_id: str, prompt: str) -> Dict[str, Any]:
    """
    Send prompt via direct HTTP API (FAST — no process spawn).
    Uses: POST /session/{id}/message
    """
    result = {"tools": [], "text": "", "errors": [], "session_id": session_id}
    try:
        url = f"{base_url.rstrip('/')}/session/{session_id}/message"
        resp = http_post(url, {"parts": [{"type": "text", "text": prompt}]})
        for part in resp.get("parts", []):
            if part.get("type") == "tool":
                result["tools"].append({
                    "name": part.get("tool", "unknown"),
                    "input": part.get("state", {}).get("input", {}),
                    "output": part.get("state", {}).get("output", {}),
                    "status": part.get("state", {}).get("status", "completed"),
                })
            elif part.get("type") == "text":
                result["text"] += part.get("text", "")
    except urllib.error.URLError as e:
        result["errors"].append(f"HTTP error: {e.reason}")
    except Exception as e:
        result["errors"].append(f"Error: {e}")
    return result


def run_opencode(
    prompt: str,
    verbose: bool = False,
    session_id: Optional[str] = None,
    attach: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run opencode CLI with a prompt and capture JSON output.
    
    Args:
        prompt: The user's prompt/message
        verbose: If True, print raw JSON events
        session_id: If provided, continue this session (--session <id>)
        attach: If provided, attach to running server (e.g., "http://localhost:4096")
        
    Returns:
        Dict with:
            - 'tools': list of tool calls with name, input, output
            - 'text': final text response from assistant
            - 'errors': any errors encountered
            - 'session_id': the session ID used (for reusing session)
    """
    result = {
        "tools": [],
        "text": "",
        "errors": [],
        "raw_events": [],
        "session_id": session_id
    }
    
    try:
        # FAST PATH: If attach, use direct HTTP API (no process spawn!)
        if attach:
            # Create session if needed
            if not session_id:
                try:
                    resp = http_post(f"{attach.rstrip('/')}/session", {})
                    session_id = resp.get("id")
                    result["session_id"] = session_id
                    if verbose:
                        print(f"{Colors.DIM}→ Created session: {session_id}{Colors.ENDC}")
                except Exception as e:
                    result["errors"].append(f"Failed to create session: {e}")
                    return result
            
            if verbose:
                print(f"{Colors.DIM}→ API: POST {attach}/session/{session_id}/message{Colors.ENDC}")
            api_result = send_via_api(attach, session_id, prompt)
            api_result["session_id"] = session_id  # Preserve session
            return api_result
        
        # SLOW PATH: Spawn opencode run (fallback)
        cmd = ["opencode", "run", "--format", "json"]
        if attach:
            cmd.extend(["--attach", attach])
        if session_id:
            cmd.extend(["--session", session_id])
        cmd.append(prompt)
        
        if verbose:
            print(f"{Colors.DIM}→ Running: {' '.join(cmd)}{Colors.ENDC}")
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        
        output_lines = []
        start_time = __import__("time").time()
        timeout = 300  # 5 min max
        
        # Read stdout line by line
        while True:
            # Check timeout
            if __import__("time").time() - start_time > timeout:
                proc.terminate()
                break
            
            line = proc.stdout.readline()
            if not line:
                # Process ended
                break
            
            output_lines.append(line)
            
            # Check if this is a terminal event (step_finish, or just finish)
            if "step_finish" in line or '"type":"finish"' in line:
                # Give it a moment to flush, then terminate
                __import__("time").sleep(0.1)
                proc.terminate()
                break
            
            # Also check for errors that would stop processing
            if '"type":"error"' in line:
                proc.terminate()
                break
        
        # Wait for process to fully end
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        
        # Combine all captured output
        output = "".join(output_lines)
        
        # Also capture any stderr
        try:
            stderr_output = proc.stderr.read()
            if stderr_output:
                output += stderr_output
        except:
            pass
        
        if verbose:
            print(f"{Colors.DIM}→ Captured {len(output_lines)} lines{Colors.ENDC}")
        
        # Parse JSON events (one per line)
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
                
            try:
                event = json.loads(line)
                result["raw_events"].append(event)
                
                # Capture session_id from first event (for session reuse)
                if result["session_id"] is None and event.get("sessionID"):
                    result["session_id"] = event["sessionID"]
                
                if verbose:
                    print(f"{Colors.DIM}  Event: {event.get('type', '?')}{Colors.ENDC}")
                
                # Handle tool_use events (MCP tool calls)
                if event.get("type") == "tool_use":
                    part = event.get("part", {})
                    tool_info = {
                        "name": part.get("tool", "unknown"),
                        "input": part.get("state", {}).get("input", {}),
                        "output": part.get("state", {}).get("output", {}),
                        "status": part.get("state", {}).get("status", "unknown"),
                    }
                    result["tools"].append(tool_info)
                
                # Handle text events (assistant response)
                elif event.get("type") == "text":
                    part = event.get("part", {})
                    text_content = part.get("text", "")
                    if text_content:
                        result["text"] += text_content
                
                # Handle errors
                elif event.get("type") == "error":
                    result["errors"].append(event.get("error", "Unknown error"))
                    
            except json.JSONDecodeError:
                # Not a JSON line, might be regular output
                if verbose and line.strip():
                    print(f"{Colors.DIM}  Non-JSON: {line[:100]}...{Colors.ENDC}")
                continue
    
    except subprocess.TimeoutExpired as e:
        # Capture any output that was produced before timeout
        # Note: e.stdout/e.stderr can be bytes even with text=True
        def _to_str(val):
            if val is None:
                return ""
            if isinstance(val, bytes):
                return val.decode("utf-8", errors="replace")
            return str(val)
        
        partial_output = ""
        if e.stdout:
            partial_output += _to_str(e.stdout)
        if e.stderr:
            partial_output += _to_str(e.stderr)
        
        # Try to parse any partial JSON events
        for line in partial_output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if event.get("type") == "error":
                    result["errors"].append(event.get("error", "Unknown error"))
            except json.JSONDecodeError:
                pass
        
        # Add helpful error with partial output
        error_msg = "Timeout: opencode took too long (>300s)"
        if partial_output:
            # Show first 800 chars of what opencode printed
            preview = partial_output[:800].replace("\n", " ")
            error_msg += f"\n    OpenCode output before timeout:\n    {preview}"
            # Also try to extract any text from text events
            for line in partial_output.strip().split("\n"):
                try:
                    event = json.loads(line)
                    if event.get("type") == "text":
                        part = event.get("part", {})
                        text_content = part.get("text", "")
                        if text_content:
                            result["text"] += text_content
                except json.JSONDecodeError:
                    pass
        else:
            error_msg += "\n    No output received. Possible issues:"
            error_msg += "\n    • opencode not configured (run 'opencode' first to set up API key)"
            error_msg += "\n    • Network issue connecting to AI provider"
            error_msg += "\n    • opencode waiting for interactive input"
        result["errors"].append(error_msg)
        
    except FileNotFoundError:
        result["errors"].append("opencode command not found. Is OpenCode installed?\n    Try: which opencode")
    except Exception as e:
        result["errors"].append(f"Exception: {str(e)}")
    
    return result


def print_tools_used(tools: List[Dict[str, Any]]):
    """Pretty-print the tools that were called."""
    if not tools:
        print(f"{Colors.YELLOW}No MCP tools were called.{Colors.ENDC}")
        return
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}┌─ MCP Tools Called ──────────────────────────────────────────┐{Colors.ENDC}")
    
    for i, tool in enumerate(tools, 1):
        name = tool.get("name", "unknown")
        status = tool.get("status", "?")
        input_args = tool.get("input", {})
        output = tool.get("output", {})
        
        # Status icon
        if status == "completed":
            status_icon = f"{Colors.GREEN}✓{Colors.ENDC}"
        elif status == "error":
            status_icon = f"{Colors.RED}✗{Colors.ENDC}"
        else:
            status_icon = f"{Colors.YELLOW}?{Colors.ENDC}"
        
        print(f"{Colors.BOLD}│ {i}. {status_icon} {name}{Colors.ENDC}")
        
        # Show input (truncated)
        if input_args:
            input_str = json.dumps(input_args, ensure_ascii=False)
            if len(input_str) > 60:
                input_str = input_str[:57] + "..."
            print(f"{Colors.DIM}│    Input:  {input_str}{Colors.ENDC}")
        
        # Show output (truncated)
        if output:
            if isinstance(output, dict):
                # MCP tool responses often have 'content' key
                if "content" in output:
                    out_str = str(output["content"])
                else:
                    out_str = json.dumps(output, ensure_ascii=False)
            else:
                out_str = str(output)
            
            if len(out_str) > 60:
                out_str = out_str[:57] + "..."
            print(f"{Colors.GREEN}│    Output: {out_str}{Colors.ENDC}")
        
        print(f"{Colors.BLUE}│{Colors.ENDC}")
    
    print(f"{Colors.BOLD}{Colors.BLUE}└──────────────────────────────────────────────────────────────┘{Colors.ENDC}\n")


def print_final_text(text: str):
    """Print the final assistant text response."""
    if not text or not text.strip():
        return
    
    print(f"{Colors.BOLD}{Colors.GREEN}Assistant:{Colors.ENDC}")
    # Indent the text
    for line in text.strip().split("\n"):
        print(f"  {line}")
    print()


def print_errors(errors: List[str]):
    """Print any errors."""
    if not errors:
        return
    
    print(f"{Colors.RED}{Colors.BOLD}Errors:{Colors.ENDC}")
    for err in errors:
        print(f"  {Colors.RED}• {err}{Colors.ENDC}")
    print()


def interactive_loop():
    """Run the interactive prompt loop."""
    print(f"""
{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗{Colors.ENDC}
{Colors.BOLD}{Colors.CYAN}║           OpenCode MCP Client - Terminal Interface           ║{Colors.ENDC}
{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════════════════╝{Colors.ENDC}

{Colors.DIM}Type your prompts below. OpenCode will automatically use MCP tools.{Colors.ENDC}
{Colors.DIM}Type 'exit', 'quit', or Ctrl+C to exit.{Colors.ENDC}
{Colors.DIM}Type 'verbose' to toggle verbose JSON output.{Colors.ENDC}

{Colors.BOLD}Available MCP tools:{Colors.ENDC} custom_test (echo, add, multiply, greet, 
                       get_current_time, reverse_text, word_count, calculate)
""")
    
    verbose = False
    current_session_id = None  # Reuse session for faster responses
    attach_url = None          # Attach to running server (e.g., http://localhost:4096)
    
    print(f"{Colors.DIM}Tip: Start 'opencode serve' in another terminal, then type:{Colors.ENDC}")
    print(f"{Colors.DIM}      attach http://localhost:4096{Colors.ENDC}")
    print(f"{Colors.DIM}  This makes prompts much faster (no process spawn per prompt).{Colors.ENDC}\n")
    
    while True:
        try:
            # Get user input
            user_input = input(f"{Colors.BOLD}>>> {Colors.ENDC}").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ("exit", "quit", "q"):
                print(f"{Colors.DIM}Goodbye!{Colors.ENDC}")
                break
            
            if user_input.lower() == "verbose":
                verbose = not verbose
                print(f"{Colors.GREEN}Verbose mode: {'ON' if verbose else 'OFF'}{Colors.ENDC}")
                continue
            
            # Command: attach <url>
            if user_input.lower().startswith("attach "):
                url = user_input.split(None, 1)[1].strip()
                attach_url = url
                print(f"{Colors.GREEN}✓ Attached to: {attach_url}{Colors.ENDC}")
                print(f"{Colors.DIM}  Prompts will now be sent to this server (fast mode).{Colors.ENDC}")
                continue
            
            if user_input.lower() == "detach":
                attach_url = None
                print(f"{Colors.YELLOW}Detached from server (local mode).{Colors.ENDC}")
                continue
            
            # Run opencode with the prompt (reuse session + attach for speed)
            print(f"{Colors.DIM}Thinking...{Colors.ENDC}")
            result = run_opencode(
                user_input,
                verbose=verbose,
                session_id=current_session_id,
                attach=attach_url
            )
            
            # Keep session for next prompt
            if result.get("session_id"):
                current_session_id = result["session_id"]
            
            # Print results
            print()
            print_tools_used(result["tools"])
            print_final_text(result["text"])
            print_errors(result["errors"])
            
        except KeyboardInterrupt:
            print(f"\n{Colors.DIM}Interrupted. Goodbye!{Colors.ENDC}")
            break
        except EOFError:
            print(f"\n{Colors.DIM}EOF. Goodbye!{Colors.ENDC}")
            break


def single_prompt(prompt: str, verbose: bool = False, session_id: Optional[str] = None):
    """Run a single prompt and print results (for scripting)."""
    result = run_opencode(prompt, verbose=verbose, session_id=session_id)
    
    print_tools_used(result["tools"])
    print_final_text(result["text"])
    print_errors(result["errors"])
    
    # Return session_id for chaining (can continue this session)
    return result.get("session_id") if result.get("session_id") else (1 if result["errors"] else 0)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Single prompt mode: python mcp_client.py "your prompt here"
        prompt = " ".join(sys.argv[1:])
        sys.exit(single_prompt(prompt))
    else:
        # Interactive mode
        interactive_loop()


if __name__ == "__main__":
    main()
