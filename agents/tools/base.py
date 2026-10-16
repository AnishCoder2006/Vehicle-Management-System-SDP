"""Base tool exceptions, metadata schemas, and configuration.
"""

import os
from typing import Any, Callable, Literal, Optional
from pydantic import BaseModel, ConfigDict


# Environment configuration
def is_mock_enabled() -> bool:
    """Check if mock tool mode is enabled (default: true)."""
    val = os.getenv("USE_MOCK_TOOLS", "true").strip().lower()
    return val in ("true", "1", "yes")


def get_api_base_url() -> str:
    """Get the backend API base URL from env or default."""
    return os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


class ToolError(Exception):
    """Normalized exception raised when a tool execution fails.
    
    Provides standardized human-readable error messages and mapped HTTP status codes.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.endpoint = endpoint
        self.details = details

    def __str__(self) -> str:
        prefix = f"[{self.status_code}] " if self.status_code else ""
        return f"{prefix}{self.message}"


class ConfirmationRequired(Exception):
    """Exception raised by write tools when called without confirmed=True.
    
    Contains the structured confirmation payload explaining what will change.
    """

    def __init__(self, action: str, summary: str, parameters: dict[str, Any]):
        super().__init__(summary)
        self.action = action
        self.summary = summary
        self.parameters = parameters


class ToolDefinition(BaseModel):
    """Metadata specification for an agent tool in the registry."""

    name: str
    description: str
    endpoint: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    action_type: Literal["read", "write"]
    owning_agent: Literal["vehicle_agent", "analytics_agent", "automation_agent"]
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    func: Optional[Callable[..., Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
