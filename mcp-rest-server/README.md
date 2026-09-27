# FastMCP REST API Server

A Model Context Protocol (MCP) server built with **FastMCP** that connects MCP clients (such as Antigravity, Claude Desktop, or custom agent runners) to external HTTPS REST APIs with authenticated user credentials.

---

## Features

- **FastMCP Framework**: Lightweight async MCP tool definitions.
- **Credential Injection**: Automatically attaches user credentials (`Bearer`, `Basic`, or custom header like `X-API-Key`) to HTTP requests.
- **Resilient Formatting**: Catches HTTP status errors (401, 403, 404, 500) and formats payloads cleanly into Markdown/JSON text responses for the LLM.
- **Payload Truncation**: Automatically caps large REST responses to prevent context window overflow.

---

## Installation & Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` or set environment variables:
   ```env
   API_BASE_URL=https://api.yourdomain.com/v1
   API_USER_TOKEN=your_secret_api_key_or_bearer_token
   AUTH_SCHEME=Bearer
   AUTH_HEADER_NAME=Authorization
   ```

3. **Test Server Locally**:
   ```bash
   python3 server.py
   ```

---

## Registration with MCP Clients

Add the server to your `mcp_config.json` (e.g. `~/.gemini/config/mcp_config.json` or `.agents/mcp_config.json`):

```json
{
  "mcpServers": {
    "rest-api-server": {
      "command": "python3",
      "args": [
        "/path/to/mcp-rest-server/server.py"
      ],
      "env": {
        "API_BASE_URL": "https://api.yourdomain.com/v1",
        "API_USER_TOKEN": "your_secret_api_key_or_bearer_token",
        "AUTH_SCHEME": "Bearer"
      }
    }
  }
}
```

---

## Exposed MCP Tools

1. **`get_resource(resource_id: str)`**: Fetches details for a specific resource via `GET /resources/{resource_id}`.
2. **`list_resources(category: str, limit: int)`**: Lists resources with optional category filter via `GET /resources`.
3. **`create_resource(name: str, description: str, category: str)`**: Creates a new resource via `POST /resources`.
4. **`delete_resource(resource_id: str)`**: Deletes a resource via `DELETE /resources/{resource_id}`.
