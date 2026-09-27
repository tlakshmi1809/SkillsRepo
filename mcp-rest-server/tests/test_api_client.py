import json
import pytest
import respx
import httpx
from api_client import RESTApiClient

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
