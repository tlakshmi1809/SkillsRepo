from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class APIResponse(BaseModel):
    """Structured response container for MCP tool execution."""
    success: bool
    status_code: int
    data: Optional[Any] = None
    error: Optional[str] = None

class CreateResourceRequest(BaseModel):
    """Schema for resource creation."""
    name: str = Field(..., description="Name of the resource to create")
    description: str = Field(..., description="Detailed description of the resource")
    category: Optional[str] = Field(None, description="Optional category filter")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Arbitrary metadata key-value pairs")
