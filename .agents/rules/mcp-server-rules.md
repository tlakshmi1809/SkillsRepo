---
trigger: always_on
description: Mandatory development rules for FastMCP REST API server code.
---

# FastMCP Server Development & Maintenance Rules

1. **Stdio Transport Safety**:
   - All logging MUST be directed strictly to `sys.stderr` via `logging.getLogger()`.
   - NEVER use plain `print()` statements in server code (`server.py`, `api_client.py`), as output on `sys.stdout` corrupts the stdio JSON-RPC protocol transport.

2. **Secret & Credential Isolation**:
   - NEVER hardcode tokens, API keys, or secrets inside Python source code.
   - Always load credentials dynamically at runtime from process environment variables or `.env` using `pydantic-settings`.

3. **Mandatory Type Annotations & Docstrings**:
   - Every MCP tool function registered with `@mcp.tool()` MUST have explicit Python type annotations for all arguments and return types.
   - Every tool MUST include a detailed docstring explaining argument purposes and return values. FastMCP uses these docstrings to generate JSON schemas for LLM tool selection.

4. **Testing Requirements**:
   - Every new tool or authentication feature MUST include automated unit tests under `tests/` using `pytest` and `respx` mock HTTP transport.

5. **Context Protection**:
   - All REST API response payloads MUST be validated and capped against `MAX_RESPONSE_CHAR_LIMIT` to protect LLM context windows from token exhaustion.
