# Developer Maintenance & Extension Guide: FastMCP REST API Server

**Target Audience**: Software Engineers, AI Platform Developers, and Codebase Maintainers  
**Document Owner**: AI Engineering & Integration Team  
**Version**: 1.3.0  
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
# Run full unit test suite (15/15 tests)
PYTHONPATH=. .venv/bin/pytest tests/ -v
```

### 1.3 Starting the Interactive Swagger UI Server
To test endpoints visually in your browser:

```bash
# Start FastAPI Swagger server on port 8000
python3 swagger_server.py
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** to test Bearer authentication and REST CRUD operations interactively.

---

## 2. Codebase Architecture & Key Files

```text
mcp-rest-server/
├── server.py                   # FastMCP server entrypoint & @mcp.tool() definitions
├── api_client.py               # Async HTTP REST client (httpx) with Auth & Tenacity retries
├── swagger_server.py           # FastAPI app serving Swagger UI (/docs) & REST CRUD routes
├── openapi.json                # Exported OpenAPI 3.1.0 specification schema
├── config.py                   # Pydantic-settings configuration & stderr logger setup
├── models.py                   # Pydantic request/response validation schemas
├── requirements.txt            # Python dependencies (fastmcp, fastapi, httpx, tenacity)
├── Dockerfile                  # Container build instructions
├── deploy.sh                   # Local container deployment script
├── deploy_cloudrun.sh          # Cloud Run deployment script
├── TECHNICAL_DESIGN.md         # Architecture blueprint & sequence diagrams
├── PRODUCTION_SUPPORT_GUIDE.md # Operational runbook for SRE/Ops
└── tests/
    ├── test_api_client.py      # Pytest test suite for API client and MCP tools
    └── test_swagger_server.py  # Pytest test suite for Swagger UI and OpenAPI endpoints
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

### 3.2 Deep Dive: Dynamic Bearer Token Injection

#### What does "Injects Authorization Bearer Token Dynamically" mean?
Instead of hardcoding API keys or passing authentication tokens inside individual tool functions, the server **automatically and dynamically attaches the `Authorization: Bearer <token>` header to every outgoing HTTP request right before it leaves the client**.

This means developers writing MCP tools in `server.py` **never need to write authentication boilerplate or handle secret tokens**.

```text
+--------------------------------------------------------------------------------------------------+
|                                    DYNAMIC AUTH INJECTION PIPELINE                               |
|                                                                                                  |
|  1. [.env File / Secrets]  ---> 2. [config.py]           ---> 3. [api_client.py]                  |
|     API_USER_TOKEN="secret"     settings.API_USER_TOKEN        _build_auth(headers)              |
|     AUTH_SCHEME="Bearer"        settings.AUTH_SCHEME           headers["Authorization"] =        |
|                                                                "Bearer " + self.token            |
|                                                                                                  |
|                                                          4. [Outgoing Request]                   |
|                                                             Authorization: Bearer secret         |
+--------------------------------------------------------------------------------------------------+
```

---

#### Step-by-Step Junior Developer Walkthrough & Setup Guide

##### Step 1: Configure Credentials in Environment (`.env`)
In your root project directory, ensure your `.env` file contains your target API credentials:

```ini
# .env file
API_BASE_URL=https://api.yourdomain.com/v1
API_USER_TOKEN=my_super_secret_jwt_or_api_token
AUTH_SCHEME=Bearer
AUTH_HEADER_NAME=Authorization
```

##### Step 2: How `config.py` Reads the Secrets
At server startup, `config.py` uses `pydantic-settings` to automatically read the `.env` file into a strongly typed `Settings` object:

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_BASE_URL: str = "https://httpbin.org"
    API_USER_TOKEN: str = ""
    AUTH_SCHEME: str = "Bearer"        # Case-insensitive: 'Bearer', 'Basic', etc.
    AUTH_HEADER_NAME: str = "Authorization"

settings = Settings()  # Auto-reads .env
```

##### Step 3: How `api_client.py` Injects the Header Dynamically
When `RESTApiClient` initializes, it receives the settings. Before executing any request (`GET`, `POST`, `PUT`, `DELETE`), `_build_auth()` constructs the exact HTTP header required by the target API:

```python
# api_client.py
class RESTApiClient:
    def __init__(self, token=None, auth_scheme=None, header_name=None):
        self.token = token or settings.API_USER_TOKEN
        self.auth_scheme = (auth_scheme or settings.AUTH_SCHEME).lower()
        self.header_name = header_name or settings.AUTH_HEADER_NAME

    def _build_auth(self, headers: Dict[str, str], params: Dict[str, Any]) -> None:
        """Dynamically injects authentication credentials into request headers."""
        if not self.token:
            return  # No token configured; skip auth

        if self.auth_scheme == "bearer":
            # Injects 'Authorization: Bearer <token>'
            headers[self.header_name] = f"Bearer {self.token}"
            
        elif self.auth_scheme == "basic":
            # Encodes basic auth if scheme is 'Basic'
            headers[self.header_name] = f"Basic {self.token}"
            
        elif self.auth_scheme == "query":
            # Appends token as query string '?api_key=<token>'
            params["api_key"] = self.token
            
        else:
            # Custom header injection (e.g. X-API-Key: <token>)
            headers[self.header_name] = self.token
```

##### Step 4: How Clean Tool Definitions Benefit (`server.py`)
Because auth is injected dynamically by the client layer, tool functions in `server.py` stay completely clean and decoupled from secret handling:

```python
# server.py - CLEAN TOOL DEFINITION (No token logic needed!)
@mcp.tool()
async def get_user_profile(user_id: str) -> str:
    """Fetch user profile by ID."""
    # Auth is automatically injected under the hood!
    return await client.get(f"/users/{user_id}")
```

##### Step 5: Verifying Dynamic Injection in Unit Tests
You can verify that dynamic Bearer token injection is working using `pytest` and `respx` in `tests/test_api_client.py`:

```python
# tests/test_api_client.py
@pytest.mark.asyncio
@respx.mock
async def test_api_client_bearer_auth():
    # 1. Mock external REST endpoint
    route = respx.get("https://api.test.com/v1/users/123").respond(
        status_code=200, json={"id": "123", "name": "Alice"}
    )

    # 2. Initialize client with Bearer scheme
    client = RESTApiClient(
        base_url="https://api.test.com/v1",
        token="secret_bearer_token",
        auth_scheme="bearer"
    )

    # 3. Call endpoint
    response = await client.get("/users/123")

    # 4. Assert header was injected dynamically
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer secret_bearer_token"
```

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
- [ ] **Unit Tests**: Run `PYTHONPATH=. .venv/bin/pytest tests/` and verify all 15 tests pass.
- [ ] **OpenAPI Spec**: Regenerate `openapi.json` if routes change (`python3 -c "..." > openapi.json`).
- [ ] **Git Push**: Commit and push changes to GitHub (`main` branch).
