# Technical Design Document: FastMCP HTTPS REST API Server

**Author**: Principal AI Systems Architect  
**Version**: 1.2.0  
**Status**: Approved / Production Ready  
**Date**: 2026-09-27  

---

## 1. Executive Summary & Goals

### 1.1 Overview
The **FastMCP HTTPS REST API Server** bridges Large Language Model (LLM) agents and external enterprise HTTPS REST endpoints using the **Model Context Protocol (MCP)**. Built on Python's `fastmcp`, `fastapi`, and `httpx`, the server translates non-deterministic natural language tool calls from MCP clients (e.g., Antigravity, Claude Desktop) into authenticated, structured HTTP requests (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`). It also provides an interactive **Swagger UI (`/docs`)** and **OpenAPI Specification (`/openapi.json`)** for developer exploration.

### 1.2 Key Objectives
- **Secure Credential Management**: Dynamically inject user credentials (`Bearer`, `Basic`, `Header`, or `Query` tokens) into outgoing REST calls without exposing credentials to LLM prompt context or stdout protocol logs.
- **Protocol Isolation**: Route operational logs strictly to `sys.stderr` so stdio transport (JSON-RPC over stdout) remains uncorrupted.
- **Fault Tolerance & Resilience**: Automatically retry transient network failures (502, 503, 504, 429) using exponential backoff with `tenacity`.
- **Context Window Protection**: Truncate large REST API payloads exceeding token thresholds (`MAX_RESPONSE_CHAR_LIMIT`) to prevent context overflow.
- **Interactive Developer Documentation**: Provide OpenAPI 3.1.0 specification and interactive Swagger UI (`/docs`) for visual endpoint inspection and interactive testing.

---

## 2. System Architecture & Topology

```
+------------------------------------------------------------------------------------------------+
|                                        MCP CLIENT RUNTIME                                      |
|  (Antigravity / Claude Desktop / Custom Agent)                                                 |
+-----------------------------------------------+------------------------------------------------+
                                                |
                                                | JSON-RPC 2.0 over stdio (stdout / stdin)
                                                v
+-----------------------------------------------+------------------------------------------------+
|                                    FASTMCP SERVER CONTAINER                                    |
|                                                                                                |
|  +---------------------------+    +----------------------------+    +-----------------------+  |
|  |       server.py           |    |       api_client.py        |    |       config.py       |  |
|  | - Tool Definitions        |--->| - httpx.AsyncClient        |<---| - Env Loader          |  |
|  | - FastMCP Router          |    | - Auth Header Injector     |    | - Stderr Logger       |  |
|  | - Schema Generator        |    | - Tenacity Retry Policy    |    |                       |  |
|  +---------------------------+    +-------------+--------------+    +-----------------------+  |
|                                                 |                                              |
|  +----------------------------------------------+-------------------------------------------+  |
|  |                          swagger_server.py (FastAPI App)                                 |  |
|  | - Interactive Swagger UI (/docs)  - ReDoc (/redoc)  - OpenAPI 3.1 Spec (/openapi.json)    |  |
|  +------------------------------------------------------------------------------------------+  |
+-------------------------------------------------|----------------------------------------------+
                                                  |
                                                  | HTTPS / TLS 1.3
                                                  v
+-------------------------------------------------+----------------------------------------------+
|                                    EXTERNAL REST API                                           |
|  (https://api.yourdomain.com/v1)                                                               |
+------------------------------------------------------------------------------------------------+
```

---

## 3. Sequence Diagram & Data Flow

```
LLM Agent                 FastMCP Server              RESTApiClient              Target REST API
    |                           |                          |                           |
    | --- 1. Call MCP Tool ---> |                          |                           |
    |     (e.g., get_resource)  |                          |                           |
    |                           | --- 2. Invoke request -> |                           |
    |                           |                          | --- 3. HTTP GET + Auth -> |
    |                           |                          |     (Inject Bearer Header)|
    |                           |                          |                           |
    |                           |                          | <--- 4. HTTP 200 JSON --- |
    |                           |                          |                           |
    |                           |                          | [Format & Truncate]       |
    |                           | <--- 5. Return String -- |                           |
    | <--- 6. Return TextContent|                          |                           |
```

---

## 4. Component Details & Specifications

### 4.1 Configuration Layer (`config.py`)
- **Settings Management**: Utilizes `pydantic-settings` to load and validate environment variables at startup.
- **Log Isolation**: Configures standard logging to `sys.stderr` to prevent log strings from polluting stdout JSON-RPC messages.

| Variable Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `API_BASE_URL` | `str` | `https://httpbin.org` | Target REST API root endpoint |
| `API_USER_TOKEN` | `str` | `""` | User credential token or API key |
| `AUTH_SCHEME` | `str` | `"Bearer"` | Auth scheme (`Bearer`, `Basic`, `Header`, `Query`) |
| `HTTP_TIMEOUT` | `float` | `30.0` | Timeout budget per HTTP call (seconds) |
| `MAX_RETRIES` | `int` | `3` | Maximum retry attempts for transient errors |

---

### 4.2 HTTP Client Layer (`api_client.py`)
- **Async Transport**: Uses `httpx.AsyncClient` for non-blocking I/O.
- **Authentication Injector**:
  - `Bearer`: Adds `Authorization: Bearer <token>`
  - `Basic`: Base64 encodes `<user>:<pass>` or raw token into `Authorization: Basic <hash>`
  - `Header`: Adds custom header (e.g. `X-API-Key: <token>`)
  - `Query`: Appends `?api_key=<token>`
- **Resilience Engine**: Implements `@retry` decorator via `tenacity`:
  - Retries on `httpx.TimeoutException`, `httpx.NetworkError`, and HTTP `502`, `503`, `504`, `429`.
  - Exponential backoff: $T_{\text{wait}} = \text{min}(0.5 \times 2^{\text{attempt}}, 5.0)$ seconds.

---

### 4.3 MCP Tool Server Layer (`server.py`)
Exposes structured CRUD tools and a generalized REST executor:

1. **`get_resource(resource_id: str)`**: Retrieves specific entity by ID.
2. **`list_resources(category: str, page: int, limit: int)`**: Paginated collection retrieval.
3. **`create_resource(name: str, description: str, category: str)`**: Constructs resource via HTTP `POST`.
4. **`update_resource(resource_id: str, updates: Dict[str, Any])`**: Updates attributes via HTTP `PATCH`.
5. **`delete_resource(resource_id: str)`**: Removes entity via HTTP `DELETE`.
6. **`execute_raw_api_request(method, endpoint, query_params, json_body)`**: Generalized execution engine with method whitelisting (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).

---

### 4.4 Swagger UI & OpenAPI Service Layer (`swagger_server.py`)
Provides interactive web documentation and schema export:

- **Swagger UI (`http://localhost:8000/docs`)**: Interactive browser interface with "Authorize" button for testing Bearer token endpoints.
- **ReDoc UI (`http://localhost:8000/redoc`)**: High-readability documentation layout.
- **OpenAPI Specification (`http://localhost:8000/openapi.json`)**: Machine-readable OpenAPI 3.1.0 schema definition for SDK generation and contract testing.

---

## 5. Workspace Rule Enforcements (`.agents/rules/`)

To ensure high codebase quality, the following rules are enforced in version control:

1. **`mcp-server-rules.md`**:
   - Stdio transport safety (logging strictly to `sys.stderr`).
   - Secret isolation (credentials loaded dynamically via `pydantic-settings`).
   - Type annotations & docstrings on all `@mcp.tool()` definitions.
   - Context window protection via response truncation (`MAX_RESPONSE_CHAR_LIMIT`).
   - Mandatory unit testing with `pytest` and `respx`.
2. **`git-workflow-rules.md`**:
   - Clear imperative commit messages.
   - Secret hygiene (.env and .venv excluded from Git).

---

## 6. Verification & Test Architecture

- **Framework**: `pytest` + `pytest-asyncio` + `fastapi.testclient`
- **Mock Transport**: `respx` for intercepting `httpx` async requests
- **Test Matrix (15/15 Passed)**:
  - `test_api_client_bearer_auth`: Validates Bearer header injection.
  - `test_api_client_basic_auth`: Validates Basic auth encoding.
  - `test_api_client_query_auth`: Validates query string token injection.
  - `test_api_client_custom_header_auth`: Validates custom header injection (`X-API-Key`).
  - `test_api_client_http_401_error_handling`: Verifies 401 error wrapping without process crashes.
  - `test_api_client_post_json`: Verifies JSON payload serialization.
  - `test_api_client_put_and_patch`: Verifies PUT/PATCH HTTP methods.
  - `test_api_client_delete`: Verifies DELETE HTTP method.
  - `test_response_truncation_rule`: Verifies payload truncation for LLM context window safety.
  - `test_server_tools_execution`: Verifies end-to-end tool calls in `server.py`.
  - `test_swagger_ui_endpoint`: Verifies `/docs` interactive Swagger UI page.
  - `test_redoc_ui_endpoint`: Verifies `/redoc` documentation page.
  - `test_openapi_json_endpoint`: Verifies OpenAPI 3.1.0 spec JSON schema generation.
  - `test_health_check_endpoint`: Verifies `/api/v1/health` status.
  - `test_authenticated_resource_crud`: Verifies REST CRUD logic under `swagger_server.py`.
