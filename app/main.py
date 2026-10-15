from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
import app.models
from app.routers import vehicles, drivers, assignments, services, costs

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vehicle Service Management API",
    description="Backend API for vehicle service management",
    version="1.0.0"
)

# Enable CORS for frontend and testing teammates
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(vehicles.router)
app.include_router(drivers.router)
app.include_router(assignments.router)
app.include_router(services.router)
app.include_router(costs.router)


@app.get("/", summary="Root health check and docs link")
def root():
    return {
        "message": "Vehicle Service API running",
        "docs": "/docs"
    }
