import pytest
from fastapi.testclient import TestClient
from swagger_server import app

client = TestClient(app)

def test_swagger_ui_endpoint():
    """Test interactive Swagger UI HTML page endpoint (/docs)."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text or "swagger-ui" in response.text

def test_redoc_ui_endpoint():
    """Test ReDoc HTML page endpoint (/redoc)."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "redoc" in response.text.lower()

def test_openapi_json_endpoint():
    """Test OpenAPI 3.1.0 specification endpoint (/openapi.json)."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "Production REST API Service"
    assert "/api/v1/resources/{resource_id}" in data["paths"]

def test_health_check_endpoint():
    """Test healthcheck endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_authenticated_resource_crud():
    """Test authenticated REST CRUD endpoints."""
    headers = {"Authorization": "Bearer test_secret_token"}

    # 1. Create Resource (POST)
    create_res = client.post(
        "/api/v1/resources",
        json={"name": "Swagger Test Item", "description": "Test Summary"},
        headers=headers
    )
    assert create_res.status_code == 201
    res_data = create_res.json()
    res_id = res_data["id"]

    # 2. Get Resource (GET)
    get_res = client.get(f"/api/v1/resources/{res_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Swagger Test Item"

    # 3. List Resources (GET)
    list_res = client.get("/api/v1/resources", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 4. Delete Resource (DELETE)
    del_res = client.delete(f"/api/v1/resources/{res_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
