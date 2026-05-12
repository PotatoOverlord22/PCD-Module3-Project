from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.audit_log import AuditLogMiddleware
from app.routers import auth_router, days, anomalies, predict, audit

app = FastAPI(
    title="Caregiver Dashboard API",
    description="Explainable Daily Activity Monitoring for Elderly Care",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditLogMiddleware)

app.include_router(auth_router.router)
app.include_router(days.router)
app.include_router(anomalies.router)
app.include_router(predict.router)
app.include_router(audit.router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "caregiver-dashboard-api"}
