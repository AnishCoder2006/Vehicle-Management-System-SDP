"""Centralized error handling, retry policies, and request_id logging.

Covers:
- API down (503 / ConnectError)
- Empty result
- 404 Not Found
- 409 Conflict
- 400 Rule violations (vehicle unavailable, invalid status progression)
- Timeout (504)
- LLM bad output
- Wrong routing / unhandled intent
"""

import contextvars
from dataclasses import dataclass
from enum import Enum
import logging
import sys
from typing import Any, Optional
import uuid

from agents.schemas import AgentResponse
from agents.tools.base import ToolError


# Context variable for request_id tracing
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="req-global")


def get_current_request_id() -> str:
    """Retrieve the active request_id from context, or generate a new one."""
    val = request_id_var.get()
    if val == "req-global":
        new_val = f"req-{uuid.uuid4().hex[:8]}"
        request_id_var.set(new_val)
        return new_val
    return val


def set_current_request_id(req_id: Optional[str] = None) -> str:
    """Set the active request_id in context."""
    val = req_id or f"req-{uuid.uuid4().hex[:8]}"
    request_id_var.set(val)
    return val


class RequestIdFilter(logging.Filter):
    """Logging filter that injects the current request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def get_agent_logger(name: str = "agent_system") -> logging.Logger:
    """Configure and return a logger with request_id formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(RequestIdFilter())
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [request_id=%(request_id)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = get_agent_logger()


class ErrorCategory(str, Enum):
    API_DOWN = "api_down"
    EMPTY_RESULT = "empty_result"
    NOT_FOUND_404 = "not_found_404"
    CONFLICT_409 = "conflict_409"
    RULE_VIOLATION_400 = "rule_violation_400"
    TIMEOUT = "timeout"
    LLM_BAD_OUTPUT = "llm_bad_output"
    WRONG_ROUTING = "wrong_routing"
    UNKNOWN = "unknown"


@dataclass
class ErrorPolicy:
    category: ErrorCategory
    retry_policy: str
    fallback: str
    user_message: str


ERROR_POLICIES: dict[ErrorCategory, ErrorPolicy] = {
    ErrorCategory.API_DOWN: ErrorPolicy(
        category=ErrorCategory.API_DOWN,
        retry_policy="2 retries with 1.0s exponential backoff",
        fallback="Inform user backend is currently offline; advise checking server port 8000.",
        user_message="The vehicle service system is currently unreachable. Please verify that the backend API is running at http://localhost:8000 and try again.",
    ),
    ErrorCategory.EMPTY_RESULT: ErrorPolicy(
        category=ErrorCategory.EMPTY_RESULT,
        retry_policy="No retries (valid empty response)",
        fallback="Return clean empty response stating no records matched query criteria.",
        user_message="No matching records were found for your request.",
    ),
    ErrorCategory.NOT_FOUND_404: ErrorPolicy(
        category=ErrorCategory.NOT_FOUND_404,
        retry_policy="No retries",
        fallback="Inform user the requested record ID does not exist in the database.",
        user_message="The requested record could not be found. Please check the ID and try again.",
    ),
    ErrorCategory.CONFLICT_409: ErrorPolicy(
        category=ErrorCategory.CONFLICT_409,
        retry_policy="No retries",
        fallback="Inform user that unique identifier already exists in system.",
        user_message="Conflict: A record with this unique identifier (license plate or driver license) already exists.",
    ),
    ErrorCategory.RULE_VIOLATION_400: ErrorPolicy(
        category=ErrorCategory.RULE_VIOLATION_400,
        retry_policy="No retries",
        fallback="Explain the exact business rule violated and what status is required.",
        user_message="Action rejected due to business rule validation.",
    ),
    ErrorCategory.TIMEOUT: ErrorPolicy(
        category=ErrorCategory.TIMEOUT,
        retry_policy="1 immediate retry with extended 5.0s timeout",
        fallback="Report operation timeout and suggest trying again.",
        user_message="The backend service timed out while processing your request. Please try again in a few moments.",
    ),
    ErrorCategory.LLM_BAD_OUTPUT: ErrorPolicy(
        category=ErrorCategory.LLM_BAD_OUTPUT,
        retry_policy="1 retry with schema strictness re-prompt",
        fallback="Fall back to deterministic rule-based output generator.",
        user_message="There was an issue formatting the response. Please try rephrasing your request.",
    ),
    ErrorCategory.WRONG_ROUTING: ErrorPolicy(
        category=ErrorCategory.WRONG_ROUTING,
        retry_policy="No retries",
        fallback="Route to Master Agent clarification prompt.",
        user_message="I'm not sure how to route that request. I can assist with vehicle operations, fleet analytics, or service maintenance alerts.",
    ),
}


def classify_error(exc: Exception) -> tuple[ErrorCategory, str]:
    """Inspect an exception and map it to an ErrorCategory and detailed message."""
    if isinstance(exc, ToolError):
        code = exc.status_code
        msg = exc.message

        if code == 503 or "cannot reach backend" in msg.lower():
            return ErrorCategory.API_DOWN, msg
        elif code == 504 or "timed out" in msg.lower():
            return ErrorCategory.TIMEOUT, msg
        elif code == 404 or "not found" in msg.lower():
            return ErrorCategory.NOT_FOUND_404, msg
        elif code == 409 or "already exists" in msg.lower() or "conflict" in msg.lower():
            return ErrorCategory.CONFLICT_409, msg
        elif code == 400 or "not available" in msg.lower() or "invalid status transition" in msg.lower():
            return ErrorCategory.RULE_VIOLATION_400, msg
        else:
            return ErrorCategory.UNKNOWN, msg

    err_str = str(exc).lower()
    if "timeout" in err_str:
        return ErrorCategory.TIMEOUT, str(exc)
    if "connection" in err_str or "connect" in err_str:
        return ErrorCategory.API_DOWN, str(exc)
    if "route" in err_str or "unclear" in err_str:
        return ErrorCategory.WRONG_ROUTING, str(exc)

    return ErrorCategory.UNKNOWN, str(exc)


def handle_agent_error(
    exc: Exception,
    agent_name: str = "agent",
    tools_called: Optional[list[str]] = None,
    request_id: Optional[str] = None,
) -> AgentResponse:
    """Translate any caught exception into a standardized AgentResponse with status='error'."""
    req_id = request_id or get_current_request_id()
    cat, raw_msg = classify_error(exc)
    policy = ERROR_POLICIES.get(cat, ErrorPolicy(
        category=ErrorCategory.UNKNOWN,
        retry_policy="No retries",
        fallback="Log traceback and return generic error message",
        user_message="An unexpected error occurred while processing your request.",
    ))

    # Formulate refined user-facing message
    if cat == ErrorCategory.RULE_VIOLATION_400:
        clean_answer = f"Validation Error: {raw_msg}"
    elif cat == ErrorCategory.NOT_FOUND_404:
        clean_answer = f"Not Found: {raw_msg}"
    elif cat == ErrorCategory.CONFLICT_409:
        clean_answer = f"Conflict: {raw_msg}"
    elif cat in (ErrorCategory.API_DOWN, ErrorCategory.TIMEOUT):
        clean_answer = policy.user_message
    else:
        clean_answer = f"{policy.user_message} (Details: {raw_msg})"

    logger.error(
        f"Handled exception in [{agent_name}] [category={cat.value}]: {raw_msg}",
        extra={"request_id": req_id},
    )

    return AgentResponse(
        status="error",
        answer=clean_answer,
        data=None,
        agent_used=agent_name,
        tools_called=tools_called or [],
        error=raw_msg,
    )
