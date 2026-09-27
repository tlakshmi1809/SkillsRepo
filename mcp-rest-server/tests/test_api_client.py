import json
import pytest
import respx
import httpx
from api_client import RESTApiClient
from config import settings
import server

@pytest.mark.asyncio
@respx.mock
async def test_api_client_bearer_auth():
    """Test that Bearer token authentication header is injected correctly."""
    route = respx.get("https://api.test.com/v1/users/123").respond(
        status_code=200,
        json={"id": "123", "name": "Alice"}
    )

    client = RESTApiClient(
        base_url="https://api.test.com/v1",
        token="secret_bearer_token",
        auth_scheme="bearer"
    )

    response = await client.get("/users/123")
    assert route.called
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer secret_bearer_token"
    assert "Alice" in response


@pytest.mark.asyncio
@respx.mock
async def test_api_client_basic_auth():
    """Test Basic Auth scheme header injection."""
    route = respx.get("https://api.test.com/v1/profile").respond(
        status_code=200,
        json={"user": "admin"}
    )

    client = RESTApiClient(
        base_url="https://api.test.com/v1",
        token="admin:password123",
        auth_scheme="basic"
    )

    response = await client.get("/profile")
    assert route.called
    request = route.calls.last.request
    assert "Basic " in request.headers["Authorization"]
    assert "admin" in response


@pytest.mark.asyncio
@respx.mock
async def test_api_client_query_auth():
    """Test Query parameter authentication injection."""
    route = respx.get("https://api.test.com/v1/data?api_key=my_query_key").respond(
        status_code=200,
        json={"data": "ok"}
    )

    client = RESTApiClient(
        base_url="https://api.test.com/v1",
        token="my_query_key",
        auth_scheme="query",
        query_param_name="api_key"
    )

    response = await client.get("/data")
    assert route.called
    assert "ok" in response


@pytest.mark.asyncio
@respx.mock
async def test_api_client_custom_header_auth():
    """Test custom API Key header injection."""
    route = respx.get("https://api.test.com/v1/secure").respond(
        status_code=200,
        json={"status": "authenticated"}
    )

    client = RESTApiClient(
        base_url="https://api.test.com/v1",
        token="custom_key_val",
        auth_scheme="header",
        header_name="X-API-Key"
    )

    response = await client.get("/secure")
    assert route.called
    request = route.calls.last.request
    assert request.headers["X-API-Key"] == "custom_key_val"


@pytest.mark.asyncio
@respx.mock
async def test_api_client_http_401_error_handling():
    """Test that HTTP 401 errors are caught and returned as clean error strings."""
    respx.get("https://api.test.com/v1/protected").respond(
        status_code=401,
        text="Unauthorized: Invalid Token"
    )

    client = RESTApiClient(
        base_url="https://api.test.com/v1",
        token="invalid_token"
    )

    response = await client.get("/protected")
    assert "HTTP Error 401" in response
    assert "Unauthorized" in response


@pytest.mark.asyncio
@respx.mock
async def test_api_client_post_json():
    """Test POST request with JSON payload."""
    route = respx.post("https://api.test.com/v1/items").respond(
        status_code=201,
        json={"status": "created", "id": "item_99"}
    )

    client = RESTApiClient(
        base_url="https://api.test.com/v1",
        token="test_token"
    )

    response = await client.post("/items", json_data={"name": "Widget"})
    assert route.called
    request = route.calls.last.request
    sent_json = json.loads(request.content)
    assert sent_json["name"] == "Widget"
    assert "item_99" in response


@pytest.mark.asyncio
@respx.mock
async def test_api_client_put_and_patch():
    """Test PUT and PATCH HTTP request methods."""
    respx.put("https://api.test.com/v1/items/1").respond(
        status_code=200, json={"updated": True}
    )
    respx.patch("https://api.test.com/v1/items/1").respond(
        status_code=200, json={"patched": True}
    )

    client = RESTApiClient(base_url="https://api.test.com/v1")
    
    put_res = await client.put("/items/1", json_data={"qty": 10})
    assert "updated" in put_res

    patch_res = await client.patch("/items/1", json_data={"qty": 5})
    assert "patched" in patch_res


@pytest.mark.asyncio
@respx.mock
async def test_api_client_delete():
    """Test DELETE HTTP request method."""
    route = respx.delete("https://api.test.com/v1/items/1").respond(
        status_code=200, json={"deleted": True}
    )

    client = RESTApiClient(base_url="https://api.test.com/v1")
    res = await client.delete("/items/1")
    assert route.called
    assert "deleted" in res


@pytest.mark.asyncio
@respx.mock
async def test_response_truncation_rule():
    """Test that large HTTP payloads are truncated to protect LLM context window (Rule 5)."""
    large_text = "A" * 15000
    respx.get("https://api.test.com/v1/large").respond(
        status_code=200,
        text=large_text
    )

    client = RESTApiClient(base_url="https://api.test.com/v1")
    res = await client.get("/large")
    assert "[Output truncated at" in res


@pytest.mark.asyncio
@respx.mock
async def test_server_tools_execution():
    """Test direct invocation of tools registered in server.py."""
    base_url = server.client.base_url.rstrip("/")
    
    respx.get(f"{base_url}/get?id=res_100").respond(status_code=200, json={"args": {"id": "res_100"}})
    respx.get(f"{base_url}/resources/res_100").respond(status_code=200, json={"id": "res_100"})
    
    respx.post(f"{base_url}/post").respond(status_code=200, json={"json": {"name": "New Item"}})
    respx.post(f"{base_url}/resources").respond(status_code=200, json={"name": "New Item"})

    get_res = await server.get_resource("res_100")
    assert "res_100" in get_res

    create_res = await server.create_resource("New Item", "Description")
    assert "New Item" in create_res

    raw_res = await server.execute_raw_api_request("GET", "/get", query_params={"id": "res_100"})
    assert "res_100" in raw_res
