# Vehicle Operations Agent (Member 3)

Entry point: `agents/vehicle_agent.py` → `run_vehicle_agent(AgentRequest) -> AgentResponse`
Tools: `agents/vehicle_tools.py` (the 14 vehicle-agent tools from the shared registry + 5 extensions)
Prompt: `agents/prompts/vehicle_prompt.py` (`VEHICLE_SYSTEM_PROMPT` + `VEHICLE_LLM_RUNTIME_RULES`)
Tests: `tests/test_vehicle_agent.py`

## Responsibilities
| Area | Tools |
|---|---|
| Vehicle CRUD (no delete) | `get_vehicles`, `get_vehicle_by_id`, `find_vehicle_by_plate`*, `create_vehicle`*, `update_vehicle`* |
| Availability | `get_available_vehicles`, `get_vehicles(status=...)` |
| Assignments | `get_drivers`, `get_driver_by_id`, `get_assignments`, `create_assignment`, `release_assignment` |
| Maintenance | `get_vehicle_maintenance`*, `get_due_service_vehicles`, `get_vehicle_history`, `create_service`, `update_service_status` |
| Costs | `create_cost` |

`*` = added by Member 3 in `vehicle_tools.py` (kept out of `agents/tools/registry.py`, which stays at the 18 endpoint wrappers).
`create_vehicle` → `POST /vehicles`, `update_vehicle` → `PUT /vehicles/{id}`. `update_vehicle` never changes `status`
(only assignments/services do) and rejects a lower mileage.

## Request pipeline
1. **Confirmation turn**: `context.action` is set → execute exactly that write (`confirmed=true`) or cancel (`confirmed=false`). No LLM.
2. **Command rules**: precise regex commands, e.g. `Assign vehicle 11 to driver 1`, `Release assignment 2`,
   `Book a brake check service for vehicle 3 on 2026-12-01`, `Update service 3 status to in_progress`,
   `Log a fuel cost of $65 for vehicle 2`, `Set mileage of vehicle 6 to 99000`,
   `Reschedule next service for vehicle 7 to 2027-01-15`, `Maintenance status for vehicle 1`,
   `History for vehicle 3`, `Is vehicle 4 available?`, `Show details for vehicle 4`.
3. **LLM loop** (when `OPENAI_API_KEY` is set and `VEHICLE_AGENT_LLM` isn't `off`): OpenAI function calling over all
   tools for free-form requests ("give the Sprinter to Jane", "what's due on KBZ-4567?").
4. **Keyword fallback**: deterministic answers when the LLM is off or fails (drivers, assignments, services,
   available vehicles by type, plate lookup, fleet listing).

## Write safety (enforced in code)
- The LLM never sees the `confirmed` parameter; any write it requests runs with `confirmed=False` (pre-checks only)
  and the loop stops with `status="needs_confirmation"`.
- Only a follow-up request with `context.confirmed=true` + `context.action` executes the write.

## Confirmation contract for the frontend (Member 5)
Turn 1 response `data` is `ConfirmationDetails`: `{action, summary, parameters, precheck_passed}`.
Turn 2: echo it back. Either form works:
```json
{"session_id": "s1", "message": "yes", "context": {"confirmed": true, "action": "update_vehicle", "parameters": {"id": 6, "mileage": 99000}}}
{"session_id": "s1", "message": "yes", "context": {"confirmed": true, "action": "create_assignment", "vehicle_id": 11, "driver_id": 1}}
```
Send `"confirmed": false` with the same `action` to cancel. Optional `context.history` (`[{role, content}]`) gives
the LLM prior chat turns; `context.customer_name` sets the customer on rule-based service bookings.

## Run
```bash
python -m pytest tests/test_vehicle_agent.py -v      # mock mode, LLM off
USE_MOCK_TOOLS=false python -c "from agents.vehicle_agent import run_vehicle_agent; from agents.schemas import AgentRequest; print(run_vehicle_agent(AgentRequest(session_id='s', message='Maintenance status for vehicle 1')))"
```
