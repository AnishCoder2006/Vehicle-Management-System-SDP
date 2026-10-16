# Open Questions for Member 2 (Backend Developer)

Prepared by **Member 1 (AI/Agent Architect)** after conducting a comprehensive audit of all route files and schemas in `app/`.

We treat your backend API as the absolute source of truth. We have not altered any backend endpoints or fields. Please review the following architectural questions so our agent tool layer aligns with your roadmap:

---

### 1. Pagination on List Endpoints
- **Current Behavior**: `GET /vehicles`, `GET /drivers`, `GET /assignments`, `GET /services`, and `GET /costs` execute `query.all()` without `limit` or `offset`.
- **Question**: When the fleet scales beyond sample data, will you introduce `limit: int = 50` and `offset: int = 0` query parameters? If so, will the response shape remain `list[...]` or become a paginated envelope `{"items": [...], "total": int}`?

---

### 2. Driver Multi-Assignment Constraint
- **Current Behavior**: In `app/routers/assignments.py`, `create_assignment` validates that the vehicle is available (`vehicle.status == "available"`). However, it does not check whether the requested driver already has an active assignment in the `Assignment` table.
- **Question**: Is a single driver allowed to be assigned to multiple active vehicles simultaneously? Or should the backend reject the assignment with `HTTP 400 Bad Request` if `Assignment.driver_id == driver_id and is_active == True`?

---

### 3. Service Booking Vehicle State Interaction
- **Current Behavior**: In `app/routers/services.py`, `POST /services` creates a service record with initial status `"pending"`. It does not verify the vehicle's current status (e.g. whether the vehicle is already `"in_service"` or assigned). Vehicle status is only changed to `"in_service"` later when `PATCH /services/{id}/status` transitions to `"in_progress"`.
- **Question**: Can a service booking be created for a vehicle that is currently assigned or in service? Or should `POST /services` validate vehicle state?

---

### 4. Search and Filtering for Drivers
- **Current Behavior**: `GET /drivers` returns all drivers. There are no query filters for name, phone, or license plate.
- **Question**: Should we plan for optional query filters like `GET /drivers?license_number=` or `GET /drivers?search=` for fast lookups?

---

### 5. Automated Alert & Webhook Endpoints
- **Current Behavior**: `GET /vehicles/due-service` identifies vehicles due within 7 days or overdue. Member 6's Automation Agent triggers maintenance notifications.
- **Question**: Will there be a dedicated backend endpoint for logging or recording sent alerts (e.g. `POST /alerts` or webhook subscriptions), or should alerts be dispatched exclusively through external messaging channels (Slack, SMS, email)?
