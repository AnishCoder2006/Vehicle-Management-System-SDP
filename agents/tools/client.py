"""HTTP client for communicating with the real FastAPI backend.

Translates HTTP status codes (409, 400, 404, 500, timeouts) into standardized ToolError exceptions.
"""

from typing import Any, Optional
import httpx

from agents.tools.base import ToolError, get_api_base_url


def request_api(
    method: str,
    endpoint: str,
    params: Optional[dict[str, Any]] = None,
    json_data: Optional[dict[str, Any]] = None,
    timeout: float = 10.0,
) -> Any:
    """Execute an HTTP request to the backend API and handle response/errors."""
    base_url = get_api_base_url()
    url = f"{base_url}{endpoint}"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method=method,
                url=url,
                params={k: v for k, v in (params or {}).items() if v is not None},
                json=json_data,
            )

        if response.status_code in (200, 201):
            return response.json()

        # Parse error detail from response
        try:
            error_json = response.json()
            detail = error_json.get("detail", response.text)
        except Exception:
            detail = response.text or f"HTTP {response.status_code}"

        if response.status_code == 404:
            raise ToolError(
                message=f"Not Found: {detail}",
                status_code=404,
                endpoint=endpoint,
                details=detail,
            )
        elif response.status_code == 409:
            raise ToolError(
                message=f"Conflict: {detail}",
                status_code=409,
                endpoint=endpoint,
                details=detail,
            )
        elif response.status_code == 400:
            raise ToolError(
                message=f"Invalid Request: {detail}",
                status_code=400,
                endpoint=endpoint,
                details=detail,
            )
        else:
            raise ToolError(
                message=f"Backend Error ({response.status_code}): {detail}",
                status_code=response.status_code,
                endpoint=endpoint,
                details=detail,
            )

    except httpx.ConnectError as exc:
        raise ToolError(
            message=f"Cannot reach backend API at {base_url}. Please ensure FastAPI is running on port 8000.",
            status_code=503,
            endpoint=endpoint,
            details=str(exc),
        ) from exc
    except httpx.TimeoutException as exc:
        raise ToolError(
            message=f"Backend API request to {endpoint} timed out after {timeout} seconds.",
            status_code=504,
            endpoint=endpoint,
            details=str(exc),
        ) from exc
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(
            message=f"Unexpected communication failure while calling {endpoint}: {exc}",
            status_code=500,
            endpoint=endpoint,
            details=str(exc),
        ) from exc
