# Vehicle Service Management : FleetFlow

A FastAPI-based vehicle and fleet management system for managing vehicles, drivers, assignments, service records, and cost logs. The project also includes a frontend dashboard and a prototype machine-learning API for estimating maintenance risk.

## Features

- Vehicle and driver management
- Vehicle assignment and release
- Service booking and status tracking
- Vehicle cost tracking and cost summaries
- Fleet statistics and service-due monitoring
- HTML, CSS, and JavaScript dashboard
- ML-based maintenance-risk prototype
- Interactive API documentation with Swagger UI

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** MySQL or SQLite
- **ORM:** SQLAlchemy
- **Frontend:** HTML, CSS, JavaScript
- **ML API:** FastAPI and scikit-learn
- **API documentation:** Swagger UI

## Project Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd Vehicle-Management-System-SDP
```

Replace `<your-repository-url>` with your repository's actual URL.

### 2. Create and activate a virtual environment

Using `uv`:

```bash
uv venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Alternatively, use Python's built-in virtual environment:

```bash
python -m venv .venv
```

Then activate it using the appropriate command above.

### 3. Install backend dependencies

Using `uv`:

```bash
uv pip install -r requirements.txt
```

Or using `pip`:

```bash
python -m pip install -r requirements.txt
```

### 4. Configure the database

Create a local environment file:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux**

```bash
cp .env.example .env
```

Configure `DATABASE_URL` in `.env` if you want to use MySQL. Use your own local database credentials; never commit real credentials to Git.

If you want to use the default SQLite setup, leave `DATABASE_URL` unset or remove its configuration from `.env`, provided your application is configured to fall back to SQLite.

Default SQLite database:

```text
sqlite:///./vehicle_service.db
```

### 5. Seed sample data

```bash
python seed.py
```

**Warning:** The seed script may clear existing records before inserting sample data. Do not run it against a database containing data you need to preserve.

### 6. Start the backend

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Open the API documentation:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Root health check: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Vehicles API: [http://127.0.0.1:8000/vehicles](http://127.0.0.1:8000/vehicles)

## Frontend Setup

The frontend is located in the `frontend/` directory and uses plain HTML, CSS, and JavaScript.

1. Start the backend on port `8000`.
2. Open the `frontend/` folder in VS Code.
3. Run `index.html` using the Live Server extension.
4. Confirm that the frontend's `API_BASE` points to your local backend:

```javascript
const API_BASE = "http://127.0.0.1:8000";
```

The backend must allow requests from the frontend's local origin, such as `http://127.0.0.1:5500`. CORS should be configured in FastAPI for the development origins you use.

The frontend communicates with FastAPI over HTTP; it does not connect directly to MySQL.

## Machine Learning — Maintenance Risk

The `ml/` directory contains a separate API and training pipeline for a maintenance-risk prediction prototype.

### ML environment

From the repository root on Windows PowerShell:

```powershell
cd ml
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Start the ML API

Keep the backend running in another terminal, then run:

```powershell
cd ml
.\.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --reload --port 8001
```

ML Swagger UI:

[http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

### Train the model

With the backend running and the ML environment activated:

```powershell
cd ml
python src\train.py
```

The training pipeline uses fleet data from the backend. Follow the ML module's configuration and dataset documentation for additional details.

### Maintenance prediction endpoint

The backend exposes:

```http
GET /vehicles/{id}/maintenance-prediction
```

For example:

```http
GET http://127.0.0.1:8000/vehicles/6/maintenance-prediction
```

The backend forwards the request to the ML API, which returns the predicted risk category, score, model version, and input features.

**Important:** This is a development prototype trained on limited sample fleet data. Its score is not a validated probability of future vehicle failure and should not be used as the sole basis for maintenance or safety decisions.

## Database and Team Development

- Each teammate can run the backend locally with their own database.
- Use `python seed.py` only when you need sample data and are comfortable with its effects on existing records.
- Frontend and agent developers should use the REST API instead of accessing the database directly.
- SQLite can be used for local development when MySQL is unavailable, if the configured fallback is enabled.
- Keep personal credentials in `.env`; commit only safe configuration examples such as `.env.example`.

## API Endpoints

### Vehicles

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root health check |
| `POST` | `/vehicles` | Create a vehicle |
| `GET` | `/vehicles` | List vehicles; supports status and vehicle-type filters |
| `GET` | `/vehicles/available` | List available vehicles |
| `GET` | `/vehicles/due-service` | List vehicles due for service within seven days or overdue |
| `GET` | `/vehicles/{id}` | Retrieve a vehicle |
| `PUT` | `/vehicles/{id}` | Update vehicle details |
| `DELETE` | `/vehicles/{id}` | Delete a vehicle, subject to assignment constraints |
| `GET` | `/vehicles/{id}/history` | Retrieve vehicle service records and cost logs |
| `GET` | `/vehicles/{id}/maintenance-prediction` | Get prototype maintenance-risk prediction |

### Drivers

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/drivers` | Create a driver |
| `GET` | `/drivers` | List drivers |
| `GET` | `/drivers/{id}` | Retrieve a driver |
| `PUT` | `/drivers/{id}` | Update driver details |
| `DELETE` | `/drivers/{id}` | Delete a driver, subject to assignment constraints |

### Assignments

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/assignments` | Assign an available vehicle to a driver |
| `GET` | `/assignments` | List assignments; supports vehicle, driver, and active-status filters |
| `POST` | `/assignments/{id}/release` | Release an assignment and return the vehicle to available status |

### Services

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/services` | Create a service booking |
| `GET` | `/services` | List service records; supports status and vehicle filters |
| `GET` | `/services/{id}` | Retrieve a service record |
| `PATCH` | `/services/{id}/status` | Update a service's status |

Allowed service-status progression:

```text
pending → in_progress → completed
```

A transition to `in_progress` sets the vehicle to `in_service`. Completing a service sets its completion date and returns the vehicle to `available`, according to the backend's implemented rules.

### Costs and Statistics

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/costs` | Create a cost entry |
| `GET` | `/costs` | List cost entries; supports vehicle and category filters |
| `GET` | `/costs/summary` | Summarize costs by vehicle, month, and overall total |
| `GET` | `/stats/summary` | Retrieve fleet and service statistics |

Supported cost categories:

```text
service, fuel, parts
```

Refer to Swagger UI at `/docs` for exact request schemas, response formats, validation rules, and available filters.

## Example Requests

### 1. Create a vehicle

**Request**

```http
POST /vehicles
Content-Type: application/json
```

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

### 2. Assign a vehicle

**Request**

```http
POST /assignments
Content-Type: application/json
```

```json
{
  "vehicle_id": 11,
  "driver_id": 1
}
```

The vehicle must be available for the assignment to succeed.

### 3. Update a service status

**Request**

```http
PATCH /services/1/status
Content-Type: application/json
```

```json
{
  "status": "in_progress"
}
```

### 4. Retrieve maintenance risk

**Request**

```http
GET /vehicles/6/maintenance-prediction
```

The response includes the vehicle ID, registration, risk category, score, model version, prediction type, and features used for the estimate. Exact values depend on the current database and trained model.

## Team Responsibilities

- **Member 1 — Master Agent:** Route user requests to the appropriate agent and coordinate responses.
- **Member 2 — Backend:** Maintain API endpoints, database models, and business logic.
- **Member 3 — Operations Agent:** Integrate vehicle, assignment, and service operations through backend API tools.
- **Member 4 — Analytics and ML:** Provide fleet statistics, cost summaries, and prototype maintenance-risk predictions.
- **Member 5 — Frontend:** Build the dashboard and connect it to the backend APIs.
- **Member 6 — Testing and Automation:** Test API behavior and build alerts or automation around service-due information.

Responsibilities may be adjusted to match the team's final agreed architecture.

## Development Notes

- Start the backend before using the frontend or training the ML model.
- Start the ML API separately when using maintenance predictions.
- Use `/docs` to inspect and test API contracts.
- Never commit `.env`, credentials, or other secrets.
- Verify endpoint behavior against the running backend because the implementation is the source of truth.

