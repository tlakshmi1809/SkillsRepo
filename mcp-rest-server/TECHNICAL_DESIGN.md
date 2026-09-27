# Technical Design Document: FastMCP HTTPS REST API Server

**Author**: Principal AI Systems Architect  
**Version**: 1.0.0  
**Status**: Approved / Production Ready  
**Date**: 2026-09-27  

---

## 1. Executive Summary & Goals

### 1.1 Overview
The **FastMCP HTTPS REST API Server** bridges Large Language Model (LLM) agents and external enterprise HTTPS REST endpoints using the **Model Context Protocol (MCP)**. Built on Python's `fastmcp` framework and `httpx`, the server translates non-deterministic natural language tool calls from MCP clients (e.g., Antigravity, Claude Desktop) into authenticated, structured HTTP requests (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).

### 1.2 Key Objectives
- **Secure Credential Management**: Dynamically inject user credentials (`Bearer`, `Basic`, `Header`, or `Query` tokens) into outgoing REST calls without exposing credentials to LLM prompt context or stdout protocol logs.
- **Protocol Isolation**: Route operational logs strictly to `sys.stderr` so stdio transport (JSON-RPC over stdout) remains uncorrupted.
- **Fault Tolerance & Resilience**: Automatically retry transient network failures (502, 503, 504, 429) using exponential backoff with `tenacity`.
- **Context Window Protection**: Truncate large REST API payloads exceeding token thresholds (`MAX_RESPONSE_CHAR_LIMIT`) to prevent context overflow.

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

## 5. Security & Risk Analysis

### 5.1 Threat Vectors & Controls

| Threat | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Credential Leakage** | High | Credentials injected via process env (`.env`); never serialized into MCP prompt output or stdio logs. |
| **Stdio Corruption** | Medium | All operational logs routed explicitly to `sys.stderr`. |
| **Context Window Overflow** | High | Response payloads capped at `MAX_RESPONSE_CHAR_LIMIT` (10,000 chars) with truncation notice. |
| **Server-Side Request Forgery (SSRF)** | High | Base URL pinned via `API_BASE_URL` settings; path traversals sanitized via `lstrip('/')`. |

---

## 6. Verification & Test Architecture

- **Framework**: `pytest` + `pytest-asyncio`
- **Mock Transport**: `respx` for intercepting `httpx` async requests
- **Test Matrix**:
  - `test_api_client_bearer_auth`: Validates correct header injection.
  - `test_api_client_http_401_error_handling`: Verifies 401 error wrapping without process crashes.
  - `test_api_client_post_json`: Verifies JSON payload serialization.
