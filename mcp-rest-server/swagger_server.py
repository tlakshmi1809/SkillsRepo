#!/usr/bin/env python3
"""
FastAPI Swagger & Mock REST API Server for FastMCP Integration.
Provides interactive Swagger UI (/docs), ReDoc (/redoc), and OpenAPI Specification (/openapi.json).
"""

from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Header, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# Initialize FastAPI App with Swagger UI
app = FastAPI(
    title="Production REST API Service",
    description=(
        "Production-grade REST API backend wrapped by the FastMCP Server. "
        "Provides interactive Swagger UI documentation, Bearer token authentication, "
        "and CRUD resource management endpoints."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Security scheme for Swagger UI "Authorize" button
security = HTTPBearer()

# --- Pydantic Data Models ---

class ResourceRequest(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Enterprise Analytics Engine"}, description="Resource name")
    description: str = Field(..., json_schema_extra={"example": "Scalable AI data processing module"}, description="Detailed summary")
    category: Optional[str] = Field("analytics", json_schema_extra={"example": "analytics"}, description="Classification category")

class ResourceResponse(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "res_1001"}, description="Unique resource identifier")
    name: str = Field(..., json_schema_extra={"example": "Enterprise Analytics Engine"})
    description: str = Field(..., json_schema_extra={"example": "Scalable AI data processing module"})
    category: Optional[str] = Field("analytics")
    status: str = Field("active", json_schema_extra={"example": "active"})

class ResourceListResponse(BaseModel):
    page: int = Field(1, json_schema_extra={"example": 1})
    limit: int = Field(10, json_schema_extra={"example": 10})
    total: int = Field(1, json_schema_extra={"example": 1})
    items: List[ResourceResponse]

# In-memory mock database
MOCK_DB: Dict[str, Dict[str, Any]] = {
    "res_1001": {
        "id": "res_1001",
        "name": "Enterprise Analytics Engine",
        "description": "Scalable AI data processing module",
        "category": "analytics",
        "status": "active"
    }
}

# --- Authentication Dependency ---

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate Bearer Token header in Swagger UI requests."""
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization Bearer token"
        )
    return token

# --- API Endpoints ---

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """Service healthcheck endpoint."""
    return {"status": "healthy", "service": "REST-API-Swagger-Server"}

@app.get(
    "/api/v1/resources/{resource_id}",
    response_model=ResourceResponse,
    tags=["Resources"],
    summary="Get Resource Details by ID"
)
async def get_resource(
    resource_id: str,
    token: str = Depends(verify_token)
):
    """Fetch details of a specific resource by ID."""
    if resource_id not in MOCK_DB:
        raise HTTPException(status_code=404, detail=f"Resource '{resource_id}' not found")
    return MOCK_DB[resource_id]

@app.get(
    "/api/v1/resources",
    response_model=ResourceListResponse,
    tags=["Resources"],
    summary="List Resources with Pagination and Filtering"
)
async def list_resources(
    category: Optional[str] = Query(None, description="Category filter"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Records per page"),
    token: str = Depends(verify_token)
):
    """List and query resources with optional category filtering and pagination."""
    filtered = list(MOCK_DB.values())
    if category:
        filtered = [item for item in filtered if item.get("category") == category]

    start = (page - 1) * limit
    end = start + limit
    paginated = filtered[start:end]

    return {
        "page": page,
        "limit": limit,
        "total": len(filtered),
        "items": paginated
    }

@app.post(
    "/api/v1/resources",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Resources"],
    summary="Create New Resource"
)
async def create_resource(
    payload: ResourceRequest,
    token: str = Depends(verify_token)
):
    """Create a new resource record."""
    new_id = f"res_{1000 + len(MOCK_DB) + 1}"
    record = {
        "id": new_id,
        "name": payload.name,
        "description": payload.description,
        "category": payload.category or "general",
        "status": "active"
    }
    MOCK_DB[new_id] = record
    return record

@app.patch(
    "/api/v1/resources/{resource_id}",
    response_model=ResourceResponse,
    tags=["Resources"],
    summary="Update Existing Resource"
)
async def update_resource(
    resource_id: str,
    updates: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """Update specific attributes of an existing resource."""
    if resource_id not in MOCK_DB:
        raise HTTPException(status_code=404, detail=f"Resource '{resource_id}' not found")
    
    record = MOCK_DB[resource_id]
    record.update(updates)
    return record

@app.delete(
    "/api/v1/resources/{resource_id}",
    tags=["Resources"],
    summary="Delete Resource by ID"
)
async def delete_resource(
    resource_id: str,
    token: str = Depends(verify_token)
):
    """Delete a resource by ID."""
    if resource_id not in MOCK_DB:
        raise HTTPException(status_code=404, detail=f"Resource '{resource_id}' not found")
    
    deleted = MOCK_DB.pop(resource_id)
    return {"status": "deleted", "id": resource_id, "name": deleted["name"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
