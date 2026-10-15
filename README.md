# Vehicle Service Management

Service for managing vehicles, drivers, assignments, service records, and cost logs.

---

### Setup (works with uv OR pip)

```bash
# create and activate virtual environment
uv venv                      # (pip users: python -m venv .venv)
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# install packages
uv pip install -r requirements.txt     # (pip users: pip install -r requirements.txt)

# configure database
cp .env.example .env         # Windows: copy .env.example .env
# edit .env with your MySQL password
# (no MySQL? delete the DATABASE_URL line and it uses SQLite automatically)

# add sample data
python seed.py

# run the server
python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`.

---

### Database for teammates

- Each person runs the backend on their own laptop with their own database, then runs `python seed.py` to get the same sample data.
- Frontend and agent developers do NOT connect to MySQL directly. They only call the API.
- If MySQL is not running or `.env` is omitted, the backend automatically defaults to local SQLite (`sqlite:///./vehicle_service.db`).

---

### Endpoint table

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Root health check and link to API docs |
| POST | `/vehicles` | Add vehicle (409 if plate exists) |
| GET | `/vehicles` | List vehicles. Optional filters `?status=` and `?vehicle_type=` |
| GET | `/vehicles/available` | List only vehicles with status `available` |
| GET | `/vehicles/due-service` | List vehicles whose `next_service_date` is within 7 days or overdue |
| GET | `/vehicles/{id}` | Get one vehicle by ID |
| PUT | `/vehicles/{id}` | Update vehicle (partial updates allowed) |
| DELETE | `/vehicles/{id}` | Delete vehicle (400 if it has an active assignment) |
| GET | `/vehicles/{id}/history` | Get that vehicle's service records and cost logs |
| POST | `/drivers` | Add driver (409 if license exists) |
| GET | `/drivers` | List all drivers |
| GET | `/drivers/{id}` | Get one driver by ID |
| PUT | `/drivers/{id}` | Update driver details |
| DELETE | `/drivers/{id}` | Delete driver (400 if it has an active assignment) |
| POST | `/assignments` | Body: `vehicle_id`, `driver_id`. Only if vehicle is `available`. Sets vehicle to `assigned` |
| POST | `/assignments/{id}/release` | Sets `released_at`, `is_active=false`, vehicle back to `available` |
| GET | `/assignments` | List assignments. Optional filters `?vehicle_id=`, `?driver_id=`, `?is_active=` |
| POST | `/services` | Create service booking (status `pending`) |
| GET | `/services` | List service records. Optional filters `?status=`, `?vehicle_id=` |
| GET | `/services/{id}` | Get one service record by ID |
| PATCH | `/services/{id}/status` | Body `{"status": "in_progress"}` or `{"status": "completed"}`. Only allowed order: `pending → in_progress → completed` |
| POST | `/costs` | Add cost entry |
| GET | `/costs` | List cost entries. Optional filters `?vehicle_id=`, `?category=` |
| GET | `/costs/summary` | Total per vehicle, total per month (format `YYYY-MM`), and grand total |
| GET | `/stats/summary` | Return counts: `{"total_vehicles", "available", "assigned", "in_service", "pending_services", "services_due_soon"}` |

---

### For teammates

- **Member 1 and 3 (agents):** wrap these as tools: `GET /vehicles`, `GET /vehicles/available`, `GET /vehicles/due-service`, `POST /assignments`, `POST /assignments/{id}/release`, `POST /services`, `PATCH /services/{id}/status`, `POST /costs`.
- **Member 4 (analytics):** `GET /stats/summary`, `GET /costs/summary`, `GET /costs?vehicle_id=`.
- **Member 5 (frontend):** base URL `http://localhost:8000`, CORS enabled (`*`), `/docs` is the contract.
- **Member 6 (testing/automation):** `GET /vehicles/due-service` for alerts; `GET /` as health check.
- **Allowed status values and transitions:**
  - `vehicle_type`: `"car"`, `"van"`, `"truck"`, `"bike"`
  - `Vehicle.status`: `"available"`, `"assigned"`, `"in_service"`
  - `Driver`: `name`, `phone`, `license_number` (unique)
  - `Assignment`: `is_active` (`true` / `false`)
  - `ServiceRecord.status`: `"pending"` → `"in_progress"` → `"completed"` (Strict transition order; skipping or reverting returns HTTP 400)
    - Transition to `in_progress` sets vehicle to `in_service`
    - Transition to `completed` sets `completed_date` to today and vehicle back to `available`
  - `CostLog.category`: `"service"`, `"fuel"`, `"parts"`

---

### Example requests

#### 1. Create Vehicle
**Request:** `POST /vehicles`
```json
{
  "plate_number": "KBZ-4567",
  "make": "Toyota",
  "model": "HiAce",
  "year": 2022,
  "vehicle_type": "van",
  "mileage": 14200,
  "status": "available",
  "next_service_date": "2026-11-15"
}
```
**Response (201 Created):**
```json
{
  "id": 11,
  "plate_number": "KBZ-4567",
  "make": "Toyota",
  "model": "HiAce",
  "year": 2022,
  "vehicle_type": "van",
  "mileage": 14200,
  "status": "available",
  "next_service_date": "2026-11-15"
}
```

#### 2. Assign Vehicle
**Request:** `POST /assignments`
```json
{
  "vehicle_id": 11,
  "driver_id": 1
}
```
**Response (201 Created):**
```json
{
  "id": 4,
  "vehicle_id": 11,
  "driver_id": 1,
  "assigned_at": "2026-10-15T18:45:00",
  "released_at": null,
  "is_active": true
}
```

#### 3. Update Service Status
**Request:** `PATCH /services/1/status`
```json
{
  "status": "in_progress"
}
```
**Response (200 OK):**
```json
{
  "id": 1,
  "vehicle_id": 1,
  "customer_name": "Apex Logistics",
  "service_type": "Routine Inspection",
  "description": "Check brake pads and all fluid levels",
  "status": "in_progress",
  "booked_date": "2026-10-13",
  "completed_date": null
}
```
