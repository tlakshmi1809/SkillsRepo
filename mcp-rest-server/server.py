#!/usr/bin/env python3
"""
FastMCP Server for Production HTTPS REST API Integration.
Exposes authenticated MCP tools wrapping external REST API endpoints.
"""

from typing import Optional, Dict, Any
from fastmcp import FastMCP
from api_client import RESTApiClient
from config import settings, logger

# Initialize FastMCP Server
mcp = FastMCP("REST-API-Integration-Server")

# Initialize HTTP REST API Client
client = RESTApiClient()


@mcp.tool()
async def get_resource(resource_id: str) -> str:
    """Fetch details of a specific resource by ID from the HTTPS REST API.

    Args:
        resource_id: The unique identifier of the resource (e.g. '12345' or 'res_abc').
    """
    endpoint = f"/get" if "httpbin.org" in settings.API_BASE_URL else f"/resources/{resource_id}"
    params = {"id": resource_id} if "httpbin.org" in settings.API_BASE_URL else None
    
    return await client.get(endpoint, params=params)


@mcp.tool()
async def list_resources(category: Optional[str] = None, page: int = 1, limit: int = 10) -> str:
    """Query and list resources from the REST API with pagination and filtering.

    Args:
        category: Optional category filter (e.g. 'finance', 'documents').
        page: Page number for pagination (default: 1).
        limit: Maximum number of records per page (default: 10).
    """
    endpoint = "/get" if "httpbin.org" in settings.API_BASE_URL else "/resources"
    params = {"page": page, "limit": limit}
    if category:
        params["category"] = category

    return await client.get(endpoint, params=params)


@mcp.tool()
async def create_resource(name: str, description: str, category: Optional[str] = None) -> str:
    """Create a new resource via HTTP POST with user credential authentication.

    Args:
        name: Name of the new resource.
        description: Summary description of the resource.
        category: Optional category classification.
    """
    endpoint = "/post" if "httpbin.org" in settings.API_BASE_URL else "/resources"
    payload = {
        "name": name,
        "description": description
    }
    if category:
        payload["category"] = category

    return await client.post(endpoint, json_data=payload)


@mcp.tool()
async def update_resource(resource_id: str, updates: Dict[str, Any]) -> str:
    """Update an existing resource via HTTP PATCH.

    Args:
        resource_id: The unique identifier of the resource to update.
        updates: Key-value dictionary of attributes to update.
    """
    endpoint = "/patch" if "httpbin.org" in settings.API_BASE_URL else f"/resources/{resource_id}"
    return await client.patch(endpoint, json_data=updates)


@mcp.tool()
async def delete_resource(resource_id: str) -> str:
    """Delete a resource by ID via HTTP DELETE.

    Args:
        resource_id: The unique identifier of the resource to delete.
    """
    endpoint = f"/delete" if "httpbin.org" in settings.API_BASE_URL else f"/resources/{resource_id}"
    return await client.delete(endpoint)


@mcp.tool()
async def execute_raw_api_request(
    method: str,
    endpoint: str,
    query_params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None
) -> str:
    """Execute a dynamic HTTP request against the REST API.

    Args:
        method: HTTP method verb ('GET', 'POST', 'PUT', 'PATCH', 'DELETE').
        endpoint: Relative path endpoint (e.g. '/users' or 'items/456').
        query_params: Optional query parameters.
        json_body: Optional JSON request payload for POST/PUT/PATCH.
    """
    allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    clean_method = method.upper().strip()
    if clean_method not in allowed_methods:
        return f"Error: Invalid HTTP method '{method}'. Allowed methods: {', '.join(allowed_methods)}"

    logger.info(f"Executing dynamic {clean_method} request to {endpoint}")
    return await client.request(
        method=clean_method,
        endpoint=endpoint,
        params=query_params,
        json_data=json_body
    )


if __name__ == "__main__":
    mcp.run()
