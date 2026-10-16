# Teammate Handoff Guide

Scaffolded and prepared by **Member 1 (AI/Agent Architect)**.  
Use this guide to start working immediately without conflicting with other teammates.

---

## Member 2: Backend Developer (FastAPI + MySQL/SQLite)
- **What was built**: A 100% compliant tool layer (`agents/tools/`) wrapping your 18 endpoints.
- **How to test with agents**:
  1. Start your backend server: `python -m uvicorn app.main:app --reload`
  2. In your terminal or `.env`, set: `USE_MOCK_TOOLS=false`
  3. Run the test suite: `python -m pytest tests/`
- **Important**: Please review `docs/OPEN_QUESTIONS.md` for our queries regarding pagination, driver assignment uniqueness, and alert webhooks.

---

## Member 3: Vehicle Operations Agent Developer
- **File to edit**: `agents/vehicle_agent.py` (search for `TODO (Member 3)`).
- **Tools you own and can call**:
  - Read: `get_vehicles`, `get_available_vehicles`, `get_vehicle_by_id`, `get_vehicle_history`, `get_drivers`, `get_driver_by_id`, `get_assignments`, `get_services`, `get_service_by_id`.
  - Write: `create_assignment`, `release_assignment`, `create_service`, `update_service_status`, `create_cost`.
- **System prompt provided**: `agents/prompts/vehicle_prompt.py` (`VEHICLE_SYSTEM_PROMPT`).
- **What to return**: A valid `AgentResponse(status=..., answer=..., data=..., agent_used="vehicle_agent", tools_called=...)`.
- **Golden rule**: NEVER call write tools with `confirmed=True` on the first user prompt. If `request.context.get("confirmed")` is False, return `status="needs_confirmation"` with the summary of what will change.

---

## Member 4: Analytics Agent Developer
- **File to edit**: `agents/analytics_agent.py` (search for `TODO (Member 4)`).
- **Tools you own and can call**:
  - `get_stats_summary()`
  - `get_costs_summary()`
  - `get_costs(vehicle_id?, category?)`
- **System prompt provided**: `agents/prompts/analytics_prompt.py` (`ANALYTICS_SYSTEM_PROMPT`).
- **ML Integration**: Integrate your predictive maintenance ML models as an additional function inside `agents/tools/operations.py` or directly inside `agents/analytics_agent.py`.
- **What to return**: A valid `AgentResponse(status="success", answer=..., data=..., agent_used="analytics_agent", tools_called=...)`.
- **Golden rule**: Strictly READ-ONLY. Never attempt to write or delete records.

---

## Member 5: Frontend Developer (Chat UI)
- **How to communicate with the Agent System**:
  - Send an `AgentRequest` JSON payload.
  - Receive an `AgentResponse` JSON payload.
- **Reference example JSONs**: Located under `docs/examples/`:
  - `docs/examples/request.json`
  - `docs/examples/response_success.json`
  - `docs/examples/response_needs_confirmation.json`
  - `docs/examples/response_partial.json`
  - `docs/examples/response_error.json`

### Chat Endpoint Contract

#### Request Format (`AgentRequest`)
```json
{
  "session_id": "sess-84920",
  "message": "Assign vehicle 11 to driver 1",
  "context": {}
}
```

#### Response Format: Action Requiring Confirmation (`status="needs_confirmation"`)
When `status == "needs_confirmation"`, show a confirmation modal or prompt in the UI with the action summary.
```json
{
  "status": "needs_confirmation",
  "answer": "You are about to assign vehicle 11 to driver 1. Assign vehicle 11 (Toyota HiAce, plate KBZ-4567) to driver 1 (John Doe). Vehicle status will change from 'available' to 'assigned'. Would you like to proceed?",
  "data": {
    "action": "create_assignment",
    "summary": "Assign vehicle 11 (Toyota HiAce, plate KBZ-4567) to driver 1 (John Doe). Vehicle status will change from 'available' to 'assigned'.",
    "parameters": {
      "vehicle_id": 11,
      "driver_id": 1
    },
    "precheck_passed": true
  },
  "agent_used": "vehicle_agent",
  "tools_called": ["create_assignment"],
  "error": null
}
```

#### Confirming the Action: Send `confirmed: true` in `context`
```json
{
  "session_id": "sess-84920",
  "message": "Yes, proceed with assigning vehicle 11 to driver 1",
  "context": {
    "confirmed": true,
    "action": "create_assignment",
    "vehicle_id": 11,
    "driver_id": 1
  }
}
```

#### Success Response
```json
{
  "status": "success",
  "answer": "Vehicle 11 successfully assigned to driver 1 (Assignment #4).",
  "data": {
    "id": 4,
    "vehicle_id": 11,
    "driver_id": 1,
    "assigned_at": "2026-10-16T08:41:00",
    "released_at": null,
    "is_active": true
  },
  "agent_used": "vehicle_agent",
  "tools_called": ["create_assignment"],
  "error": null
}
```

---

## Member 6: Automation & Testing Developer
- **File to edit**: `agents/automation_agent.py` (search for `TODO (Member 6)`).
- **Tools you own and can call**:
  - `get_due_service_vehicles()` (identifies vehicles due within 7 days or overdue).
- **System prompt provided**: `agents/prompts/automation_prompt.py` (`AUTOMATION_SYSTEM_PROMPT`).
- **Automation / Workflows**: Connect scheduled cron jobs, notification dispatchers (e.g. email, SMS, webhooks), and health checks here.
- **Running tests**:
  ```bash
  python -m pytest tests/ -v
  ```
- **Golden rule**: Read-only on data. Hand off service booking requests to Member 3's Vehicle Operations Agent.
