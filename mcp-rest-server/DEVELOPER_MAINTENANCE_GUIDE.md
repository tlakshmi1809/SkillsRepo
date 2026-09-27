# Developer Maintenance & Extension Guide: FastMCP REST API Server

**Target Audience**: Software Engineers, AI Platform Developers, and Codebase Maintainers  
**Document Owner**: AI Engineering & Integration Team  
**Version**: 1.1.0  
**Last Updated**: 2026-09-27  

---

## 1. Developer Quick Start & Environment Setup

### 1.1 Local Virtual Environment
To set up a local development environment with all required tools, dependencies, and test libraries:

```bash
cd mcp-rest-server

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies in editable mode
pip install -r requirements.txt
```

### 1.2 Running Local Tests
Run the automated unit test suite using `pytest`:

```bash
# Run unit tests with respx HTTP mocking
PYTHONPATH=. .venv/bin/pytest tests/ -v
```

---

## 2. Codebase Architecture & Key Files

```text
mcp-rest-server/
├── server.py                   # FastMCP server entrypoint & @mcp.tool() definitions
├── api_client.py               # Async HTTP REST client (httpx) with Auth & Tenacity retries
├── config.py                   # Pydantic-settings configuration & stderr logger setup
├── models.py                   # Pydantic request/response validation schemas
├── requirements.txt            # Python dependencies (fastmcp, httpx, tenacity, pydantic)
├── Dockerfile                  # Container build instructions
├── deploy.sh                   # Local container deployment script
├── deploy_cloudrun.sh          # Cloud Run deployment script
├── TECHNICAL_DESIGN.md         # Architecture blueprint & sequence diagrams
├── PRODUCTION_SUPPORT_GUIDE.md # Operational runbook for SRE/Ops
└── tests/
    └── test_api_client.py      # Pytest test suite with respx mocks
```

---

## 3. Developer Workflows & How-To Guides

### 3.1 How to Add a New MCP Tool Endpoint

To expose a new REST API endpoint as an MCP Tool for LLM agents:

1. Open [`server.py`](file:///config/Desktop/Session1/mcp-rest-server/server.py).
2. Define an `async` function decorated with `@mcp.tool()`.
3. Provide explicit Python type hints and a comprehensive docstring (FastMCP uses the docstring to generate tool descriptions for LLM tool selection).

#### Example: Adding a `search_documents` Tool

```python
@mcp.tool()
async def search_documents(query: str, max_results: int = 5) -> str:
    """Search enterprise document repository by keyword or phrase.

    Args:
        query: Search term or query phrase.
        max_results: Maximum number of matching documents to return (default: 5).
    """
    endpoint = "/documents/search"
    params = {
        "q": query,
        "limit": max_results
    }
    
    # Delegates request execution, auth injection, and error handling to client
    return await client.get(endpoint, params=params)
```

---

### 3.2 Deep Dive: The Client Delegation Architecture

When a tool function in `server.py` invokes `await client.get(endpoint, params=params)`, it delegates **5 core operational responsibilities** to `RESTApiClient` in [`api_client.py`](file:///config/Desktop/Session1/mcp-rest-server/api_client.py):

```
+-----------------------------------------------------------------------------------+
| TOOL LAYER (server.py)                                                            |
| @mcp.tool() async def search_documents(query, limit):                            |
|     return await client.get("/documents/search", params={"q": query})              |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Delegates 5 Core Functions
                                          v
+-----------------------------------------------------------------------------------+
| CLIENT LAYER (api_client.py -> RESTApiClient)                                     |
|                                                                                   |
|  1. URL Normalization   : Merges base URL & path (https://api.com/v1/docs/search)  |
|  2. Auth Injection      : Injects 'Authorization: Bearer <token>' dynamically     |
|  3. Tenacity Retries    : Retries 502/503/504/429 with exponential backoff         |
|  4. Exception Safety    : Traps 4xx/5xx & network drops -> Returns clean error msg |
|  5. Response Protection : Formats JSON & truncates if > MAX_RESPONSE_CHAR_LIMIT   |
+-----------------------------------------------------------------------------------+
```

#### 1. URL Normalization & Request Assembly
- Strips leading slashes and joins the endpoint with `API_BASE_URL` (`https://api.yourdomain.com/v1` + `documents/search`).
- Assembles default standard headers (`User-Agent: FastMCP-REST-Client/1.0`, `Accept: application/json`, `Content-Type: application/json`).

#### 2. Dynamic Credential & Auth Injection (`_build_auth`)
- Evaluates `settings.AUTH_SCHEME` (`Bearer`, `Basic`, `Header`, `Query`).
- Injects credentials directly into HTTP request headers or query strings without exposing secret tokens to tool definitions, LLM prompt text, or stdout logs.

#### 3. Fault Tolerance & Exponential Backoff Retries (`tenacity`)
- Wraps request execution with `@retry(stop=stop_after_attempt(3), wait=wait_exponential())`.
- Automatically catches transient status codes (`502`, `503`, `504`, `429`) and network connection drops, retrying with backoff ($0.5\text{s} \rightarrow 1.0\text{s} \rightarrow 2.0\text{s}$) before failing.

#### 4. Exception Wrapping & Stdio Safety
- Catches `httpx.HTTPStatusError` (401, 403, 404, 500) and `httpx.RequestError` (DNS failure, refused connections).
- Formats errors as clean strings (e.g. `"HTTP Error 401: Unauthorized"`) rather than raising unhandled Python tracebacks.
- **Critical Requirement**: Prevents process crashes that would terminate the stdio JSON-RPC loop between the MCP server and LLM runtime.

#### 5. Response Sanitization & Token Truncation (`_format_response`)
- Pretty-prints JSON responses with `indent=2` for model scannability.
- Enforces `MAX_RESPONSE_CHAR_LIMIT` (default: 10,000 characters). If a REST response is oversized, it appends a truncation notice to protect the model's context window.

---

### 3.3 How to Extend Authentication Mechanisms

Authentication logic is encapsulated inside `RESTApiClient._build_auth()` in [`api_client.py`](file:///config/Desktop/Session1/mcp-rest-server/api_client.py).

#### Example: Adding HMAC Signature Authentication

If a target REST API requires HMAC request signing:

```python
import hmac
import hashlib
import time

def _build_auth(self, headers: Dict[str, str], params: Dict[str, Any]) -> None:
    if not self.token:
        return

    if self.auth_scheme == "hmac":
        timestamp = str(int(time.time()))
        signature = hmac.new(
            self.token.encode("utf-8"),
            timestamp.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        headers["X-Signature"] = signature
        headers["X-Timestamp"] = timestamp
    else:
        # Existing Bearer / Basic / Header / Query schemes...
        pass
```

---

### 3.4 How to Customize Response Transformers

Response formatting and character truncation are handled in `RESTApiClient._format_response()` in [`api_client.py`](file:///config/Desktop/Session1/mcp-rest-server/api_client.py).

To filter out sensitive fields (e.g., SSN, credit card numbers) before returning data to the MCP client:

```python
def _format_response(self, response: httpx.Response) -> str:
    try:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = response.json()
            
            # Custom Transformer: Redact sensitive fields
            if isinstance(payload, dict):
                payload.pop("password_hash", None)
                payload.pop("ssn", None)

            formatted = json.dumps(payload, indent=2)
        else:
            formatted = response.text

        # Truncate if exceeding token safety threshold
        if len(formatted) > settings.MAX_RESPONSE_CHAR_LIMIT:
            formatted = (
                formatted[:settings.MAX_RESPONSE_CHAR_LIMIT]
                + f"\n\n... [Output truncated at {settings.MAX_RESPONSE_CHAR_LIMIT} characters]"
            )

        return formatted
    except Exception as err:
        return f"Raw Response ({response.status_code}): {response.text[:1000]}"
```

---

## 4. Testing & Quality Assurance Guidelines

All code modifications must be accompanied by corresponding unit tests.

### 4.1 Writing a New Unit Test
Add test cases in `tests/test_api_client.py` using `respx` to mock external HTTP endpoints without making real network calls.

```python
@pytest.mark.asyncio
@respx.mock
async def test_search_documents():
    """Test search_documents tool endpoint invocation."""
    route = respx.get("https://httpbin.org/documents/search?q=invoice&limit=5").respond(
        status_code=200,
        json={"results": [{"id": "doc_1", "title": "Invoice 2026"}]}
    )

    client = RESTApiClient(base_url="https://httpbin.org")
    response = await client.get("/documents/search", params={"q": "invoice", "limit": 5})
    
    assert route.called
    assert "Invoice 2026" in response
```

---

## 5. Maintenance Checklist for Developers

When modifying or deploying changes:

- [ ] **Type Annotations**: Ensure all tool parameters have explicit Python types.
- [ ] **Docstrings**: Verify function docstrings clearly explain tool purpose and arguments.
- [ ] **No stdout `print()`**: Check that no `print()` statements exist in codebase (use `logger.info()` / `logger.error()`).
- [ ] **Unit Tests**: Run `PYTHONPATH=. .venv/bin/pytest tests/` and verify all tests pass.
- [ ] **Git Push**: Commit and push changes to GitHub (`main` branch).
