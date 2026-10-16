"""Vehicle Operations Agent (Member 3).

Handles:
- Vehicle CRUD (list, details, plate lookup, register, update; never delete)
- Availability (available vehicles, per-vehicle availability)
- Driver directory
- Driver assignments and releases (requires confirmation)
- Service bookings and status progression: pending -> in_progress -> completed (requires confirmation)
- Maintenance snapshots (next service date, overdue / due soon, open jobs)
- Cost logging (requires confirmation)

Request pipeline (first match wins):
1. Confirmation turn  - context has confirmed=True + action: execute that exact write, no LLM involved.
2. Command rules      - precise regex commands ("assign vehicle 11 to driver 1", "maintenance for vehicle 3").
3. LLM agent loop     - OpenAI function calling over VEHICLE_TOOLS for free-form questions.
4. Keyword fallback   - deterministic answers when the LLM is disabled or fails.

Write safety is enforced in code, not by the prompt: the LLM never sees the
`confirmed` parameter, every write it requests runs with confirmed=False, and the
loop stops at the first ConfirmationRequiredOutput and returns needs_confirmation.
"""

import json
import os
import re
from datetime import date
from typing import Any, Optional

from pydantic import ValidationError

from agents.errors import get_agent_logger, handle_agent_error, set_current_request_id
from agents.prompts.vehicle_prompt import VEHICLE_LLM_RUNTIME_RULES, VEHICLE_SYSTEM_PROMPT
from agents.schemas import AgentRequest, AgentResponse, ConfirmationDetails
from agents.tools.base import ToolError
from agents.tools.models import ConfirmationRequiredOutput
from agents.vehicle_tools import VEHICLE_TOOLS, WRITE_ACTIONS, call_tool, to_jsonable

logger = get_agent_logger("vehicle_agent")

AGENT_NAME = "vehicle_agent"
MAX_LLM_STEPS = 6
VEHICLE_TYPES = ("car", "van", "truck", "bike")


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------
def _success(answer: str, data: Any, tools_called: list[str]) -> AgentResponse:
    return AgentResponse(status="success", answer=answer, data=data, agent_used=AGENT_NAME,
                         tools_called=tools_called)


def _needs_confirmation(result: ConfirmationRequiredOutput, tools_called: list[str]) -> AgentResponse:
    details = ConfirmationDetails(action=result.action, summary=result.summary,
                                  parameters=result.parameters, precheck_passed=result.precheck_passed)
    return AgentResponse(
        status="needs_confirmation",
        answer=f"{result.summary} Would you like to proceed?",
        data=details.model_dump(mode="json"),
        agent_used=AGENT_NAME,
        tools_called=tools_called,
    )


def _write(action: str, args: dict[str, Any], confirmed: bool, tools_called: list[str]) -> AgentResponse:
    """Run a write tool: returns needs_confirmation, or success after a confirmed execution."""
    tools_called.append(action)
    result = call_tool(action, args, confirmed=confirmed)
    if isinstance(result, ConfirmationRequiredOutput):
        return _needs_confirmation(result, tools_called)
    return _success(_describe_write(action, result), to_jsonable(result), tools_called)


def _describe_write(action: str, r: Any) -> str:
    if action == "create_assignment":
        return f"Vehicle {r.vehicle_id} successfully assigned to driver {r.driver_id} (Assignment #{r.id})."
    if action == "release_assignment":
        return f"Assignment #{r.id} has been released. Vehicle {r.vehicle_id} is now available."
    if action == "create_service":
        return (f"Service booking #{r.id} ('{r.service_type}') created for vehicle {r.vehicle_id} "
                f"on {r.booked_date} with status 'pending'.")
    if action == "update_service_status":
        return f"Service record #{r.id} status updated to '{r.status}'."
    if action == "create_cost":
        return f"Cost entry #{r.id} (${r.amount:.2f} {r.category}) logged for vehicle {r.vehicle_id}."
    if action == "create_vehicle":
        return f"Vehicle #{r.id} ({r.plate_number}) registered and available for assignment."
    if action == "update_vehicle":
        return f"Vehicle #{r.id} ({r.plate_number}) updated."
    return f"Action '{action}' completed."


def _vehicle_line(v) -> str:
    name = " ".join(p for p in (v.make, v.model) if p) or "Vehicle"
    return f"{name} (Plate: {v.plate_number}, ID: {v.id})"


# ---------------------------------------------------------------------------
# 1. Confirmation turn
# ---------------------------------------------------------------------------
def _confirmation_params(action: str, context: dict[str, Any]) -> dict[str, Any]:
    """Pull the write parameters from context: either context['parameters'] (the
    ConfirmationDetails payload echoed back) or flat keys as in docs/HANDOFF.md."""
    source = context.get("parameters") if isinstance(context.get("parameters"), dict) else context
    fields = VEHICLE_TOOLS[action].input_model.model_fields
    return {k: v for k, v in source.items() if k in fields and k != "confirmed"}


def _handle_pending_action(context: dict[str, Any], tools_called: list[str]) -> AgentResponse:
    action = context["action"]
    if action not in WRITE_ACTIONS:
        raise ToolError(f"Unknown or non-write action '{action}' cannot be confirmed", status_code=400)
    if not context.get("confirmed"):
        return _success("Okay, I cancelled that action. No changes were made.", None, tools_called)
    return _write(action, _confirmation_params(action, context), True, tools_called)


# ---------------------------------------------------------------------------
# 2. Precise command rules
# ---------------------------------------------------------------------------
def _run_command_rules(request: AgentRequest, confirmed: bool, tools_called: list[str]) -> Optional[AgentResponse]:
    text = request.message.lower().strip()

    if m := re.search(r"assign\s+vehicle\s+(\d+)\s+to\s+driver\s+(\d+)", text):
        return _write("create_assignment", {"vehicle_id": int(m[1]), "driver_id": int(m[2])}, confirmed, tools_called)

    if m := re.search(r"release\s+assignment\s+#?(\d+)", text):
        return _write("release_assignment", {"id": int(m[1])}, confirmed, tools_called)

    if m := re.search(r"update\s+service\s+(?:record\s+)?#?(\d+)\s+status\s+to\s+(in[\s_]progress|completed|pending)", text):
        status = m[2].replace(" ", "_")
        return _write("update_service_status", {"id": int(m[1]), "status": status}, confirmed, tools_called)

    if m := re.search(r"book\s+(?:an?\s+)?(.+?)\s+service\s+for\s+vehicle\s+(\d+)", text):
        service_type = m[1].title()
        args = {"vehicle_id": int(m[2]),
                "customer_name": request.context.get("customer_name", "Fleet Operations"),
                "service_type": service_type,
                "description": f"Booked via agent: {service_type}"}
        if d := re.search(r"\bon\s+(\d{4}-\d{2}-\d{2})", text):
            args["booked_date"] = d[1]
        return _write("create_service", args, confirmed, tools_called)

    if m := re.search(r"log\s+(?:a\s+)?(fuel|service|parts)\s+cost\s+of\s+\$?(\d+(?:\.\d+)?)\s+for\s+vehicle\s+(\d+)", text):
        args = {"vehicle_id": int(m[3]), "category": m[1], "amount": float(m[2]),
                "description": f"{m[1].capitalize()} logged via agent"}
        return _write("create_cost", args, confirmed, tools_called)

    if m := re.search(r"(?:set|update|change)\s+(?:the\s+)?mileage\s+(?:of|for)\s+vehicle\s+(\d+)\s+to\s+([\d,]+)", text):
        return _write("update_vehicle", {"id": int(m[1]), "mileage": int(m[2].replace(",", ""))},
                      confirmed, tools_called)

    if m := re.search(r"(?:set|update|change|reschedule)\s+(?:the\s+)?next\s+service\s+(?:date\s+)?(?:of|for)\s+"
                      r"vehicle\s+(\d+)\s+to\s+(\d{4}-\d{2}-\d{2})", text):
        return _write("update_vehicle", {"id": int(m[1]), "next_service_date": m[2]}, confirmed, tools_called)

    if m := re.search(r"maintenance\s+(?:status\s+|details\s+)?(?:of|for)\s+vehicle\s+(\d+)|vehicle\s+(\d+)\s+maintenance", text):
        return _maintenance(int(m[1] or m[2]), tools_called)

    if m := re.search(r"history\s+(?:of|for)\s+vehicle\s+(\d+)", text):
        v_id = int(m[1])
        tools_called.append("get_vehicle_history")
        hist = call_tool("get_vehicle_history", {"id": v_id})
        return _success(
            f"Vehicle {v_id} history: {len(hist.service_records)} service records, {len(hist.cost_logs)} cost logs.",
            to_jsonable(hist), tools_called)

    if m := re.search(r"\bis\s+vehicle\s+(\d+)\s+available", text):
        tools_called.append("get_vehicle_by_id")
        v = call_tool("get_vehicle_by_id", {"id": int(m[1])})
        verdict = "is available" if v.status == "available" else f"is not available (status: {v.status})"
        return _success(f"{_vehicle_line(v)} {verdict}.", to_jsonable(v), tools_called)

    if m := re.search(r"(?:details|info)\s+(?:of|for|on)\s+vehicle\s+(\d+)|^(?:show|get)\s+vehicle\s+(\d+)\.?$", text):
        tools_called.append("get_vehicle_by_id")
        v = call_tool("get_vehicle_by_id", {"id": int(m[1] or m[2])})
        return _success(
            f"{_vehicle_line(v)}: {v.year or 'unknown year'} {v.vehicle_type}, {v.mileage} km, status '{v.status}', "
            f"next service {v.next_service_date or 'not scheduled'}.", to_jsonable(v), tools_called)

    return None


def _maintenance(vehicle_id: int, tools_called: list[str]) -> AgentResponse:
    tools_called.append("get_vehicle_maintenance")
    snap = call_tool("get_vehicle_maintenance", {"id": vehicle_id})
    days = snap.days_until_service
    when = {
        "overdue": f"OVERDUE by {-days} day(s) (was due {snap.next_service_date})" if days is not None else "",
        "due_soon": f"due in {days} day(s) on {snap.next_service_date}",
        "ok": f"next service in {days} day(s) on {snap.next_service_date}",
        "unscheduled": "no next service date scheduled",
    }[snap.maintenance_state]
    open_jobs = len(snap.open_service_records)
    answer = (f"{_vehicle_line(snap.vehicle)} is {when}. Open service jobs: {open_jobs}. "
              f"Completed services: {snap.completed_service_count}. "
              f"Total cost logged: ${snap.total_cost_logged:.2f}.")
    if snap.maintenance_state in ("overdue", "due_soon") and open_jobs == 0:
        answer += f" Recommend booking a service: e.g. 'Book a routine inspection service for vehicle {vehicle_id}'."
    return _success(answer, to_jsonable(snap), tools_called)


# ---------------------------------------------------------------------------
# 3. LLM agent loop (OpenAI function calling)
# ---------------------------------------------------------------------------
def _llm_enabled() -> bool:
    mode = os.getenv("VEHICLE_AGENT_LLM", "auto").strip().lower()
    if mode in ("off", "false", "0", "no"):
        return False
    return bool(os.getenv("OPENAI_API_KEY"))


def _llm_messages(request: AgentRequest) -> list[dict[str, Any]]:
    system = f"{VEHICLE_SYSTEM_PROMPT}\n{VEHICLE_LLM_RUNTIME_RULES}\nToday's date: {date.today().isoformat()}"
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for turn in request.context.get("history") or []:
        if isinstance(turn, dict) and turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": str(turn["content"])})
    messages.append({"role": "user", "content": request.message})
    return messages


def _run_llm_agent(request: AgentRequest, tools_called: list[str]) -> AgentResponse:
    from openai import OpenAI  # imported lazily so rule/mock mode works without the package configured

    client = OpenAI(timeout=60, max_retries=2)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    messages = _llm_messages(request)
    specs = [t.openai_spec() for t in VEHICLE_TOOLS.values()]
    last_data: Any = None

    for _ in range(MAX_LLM_STEPS):
        msg = client.chat.completions.create(
            model=model, messages=messages, tools=specs, tool_choice="auto",
        ).choices[0].message
        calls = [c for c in (msg.tool_calls or []) if c.type == "function"]

        if not calls:
            answer = (msg.content or "").strip()
            if not answer:
                raise ValueError("LLM returned an empty answer")
            return _success(answer, last_data, tools_called)

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments}}
                           for c in calls],
        })
        for call in calls:
            name = call.function.name
            tools_called.append(name)
            result = _execute_llm_tool_call(name, call.function.arguments)
            if isinstance(result, ConfirmationRequiredOutput):
                # Hard stop: a write was requested. The user must confirm on the next turn.
                return _needs_confirmation(result, tools_called)
            payload = to_jsonable(result)
            if not (isinstance(payload, dict) and "error" in payload):
                last_data = payload
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(payload, default=str)})

    return AgentResponse(
        status="partial",
        answer="I gathered some information but could not finish within the step limit. "
               "Please make the request more specific (e.g. include the vehicle or driver ID).",
        data=last_data, agent_used=AGENT_NAME, tools_called=tools_called,
    )


def _execute_llm_tool_call(name: str, raw_args: str) -> Any:
    """Run one LLM-requested tool. Writes always run unconfirmed (they only pre-validate).
    Recoverable problems are returned to the model as {"error": ...} so it can explain or retry."""
    if name not in VEHICLE_TOOLS:
        return {"error": f"Unknown tool '{name}'"}
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        return {"error": "Tool arguments were not valid JSON"}
    try:
        return call_tool(name, args, confirmed=False)
    except ValidationError as e:
        return {"error": "Invalid arguments", "details": e.errors(include_url=False, include_context=False)}
    except ToolError as e:
        if e.status_code in (503, 504):
            raise  # backend down / timeout: surface through the standard error policy
        return {"error": e.message, "status_code": e.status_code}


# ---------------------------------------------------------------------------
# 4. Deterministic keyword fallback (no LLM)
# ---------------------------------------------------------------------------
def _run_keyword_fallback(request: AgentRequest, tools_called: list[str]) -> AgentResponse:
    text = request.message.lower()

    if "driver" in text:
        tools_called.append("get_drivers")
        drivers = call_tool("get_drivers", {})
        if not drivers:
            return _success("No registered drivers found in the system.", [], tools_called)
        names = [f"{d.name} (ID: {d.id}, License: {d.license_number})" for d in drivers]
        return _success(f"Found {len(drivers)} registered drivers: {', '.join(names)}.",
                        to_jsonable(drivers), tools_called)

    if "assignment" in text:
        active_only = "active" in text or "current" in text
        tools_called.append("get_assignments")
        rows = call_tool("get_assignments", {"is_active": True} if active_only else {})
        label = "active assignment(s)" if active_only else "assignment(s)"
        lines = [f"#{a.id}: vehicle {a.vehicle_id} -> driver {a.driver_id}" for a in rows]
        return _success(f"Found {len(rows)} {label}" + (f": {'; '.join(lines)}." if lines else "."),
                        to_jsonable(rows), tools_called)

    if "service" in text and any(w in text for w in ("pending", "in progress", "in_progress", "records", "bookings")):
        status = "pending" if "pending" in text else ("in_progress" if "progress" in text else None)
        tools_called.append("get_services")
        rows = call_tool("get_services", {"status": status} if status else {})
        lines = [f"#{s.id} {s.service_type} (vehicle {s.vehicle_id}, {s.status})" for s in rows]
        return _success(f"Found {len(rows)} service record(s)" + (f": {'; '.join(lines)}." if lines else "."),
                        to_jsonable(rows), tools_called)

    v_type = next((t for t in VEHICLE_TYPES if re.search(rf"\b{t}s?\b", text)), None)
    if "available" in text:
        if v_type:
            tools_called.append("get_vehicles")
            vehicles = call_tool("get_vehicles", {"status": "available", "vehicle_type": v_type})
        else:
            tools_called.append("get_available_vehicles")
            vehicles = call_tool("get_available_vehicles", {})
        if not vehicles:
            type_msg = f" of type '{v_type}'" if v_type else ""
            return _success(f"No available vehicles found{type_msg}.", [], tools_called)
        return _success(f"Found {len(vehicles)} available vehicle(s): {', '.join(_vehicle_line(v) for v in vehicles)}.",
                        to_jsonable(vehicles), tools_called)

    if m := re.search(r"\b([a-z]{3}-\d{3,4})\b", text):
        tools_called.append("find_vehicle_by_plate")
        v = call_tool("find_vehicle_by_plate", {"plate_number": m[1]})
        return _success(f"{_vehicle_line(v)}: status '{v.status}', {v.mileage} km, "
                        f"next service {v.next_service_date or 'not scheduled'}.", to_jsonable(v), tools_called)

    tools_called.append("get_vehicles")
    vehicles = call_tool("get_vehicles", {"vehicle_type": v_type} if v_type else {})
    by_status: dict[str, int] = {}
    for v in vehicles:
        by_status[v.status] = by_status.get(v.status, 0) + 1
    breakdown = ", ".join(f"{n} {s}" for s, n in sorted(by_status.items()))
    scope = f"{v_type}s" if v_type else "vehicles"
    return _success(f"Total {len(vehicles)} {scope} in the fleet" + (f" ({breakdown})." if breakdown else "."),
                    to_jsonable(vehicles), tools_called)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def run_vehicle_agent(request: AgentRequest) -> AgentResponse:
    """Entrypoint for the Vehicle Operations Agent.

    Accepts standardized AgentRequest and returns AgentResponse.
    Works on mock tools out of the box; set USE_MOCK_TOOLS=false for the live API
    and OPENAI_API_KEY to enable the LLM loop for free-form requests.
    """
    req_id = set_current_request_id(request.context.get("request_id"))
    logger.info(f"Processing request: '{request.message}'", extra={"request_id": req_id})
    tools_called: list[str] = []
    context = request.context
    confirmed = bool(context.get("confirmed", False))

    try:
        if context.get("action"):
            return _handle_pending_action(context, tools_called)

        response = _run_command_rules(request, confirmed, tools_called)
        if response is not None:
            return response

        if _llm_enabled():
            try:
                return _run_llm_agent(request, tools_called)
            except ToolError:
                raise
            except Exception as exc:  # LLM_BAD_OUTPUT / provider errors -> deterministic fallback
                logger.warning(f"LLM loop failed, using rule-based fallback: {exc}", extra={"request_id": req_id})
                tools_called.clear()

        return _run_keyword_fallback(request, tools_called)

    except ValidationError as exc:
        first = exc.errors(include_url=False)[0]
        field = ".".join(str(p) for p in first.get("loc", ()))
        return handle_agent_error(
            ToolError(f"Invalid value for '{field}': {first.get('msg')}", status_code=400),
            agent_name=AGENT_NAME, tools_called=tools_called, request_id=req_id,
        )
    except Exception as exc:
        return handle_agent_error(exc=exc, agent_name=AGENT_NAME, tools_called=tools_called, request_id=req_id)
