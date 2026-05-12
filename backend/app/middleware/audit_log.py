from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

audit_entries = []

ACTION_MAP = {
    ("POST", "/auth/login"): "logged in",
    ("GET", "/days"): "viewed all days",
    ("GET", "/anomalies"): "viewed anomalies list",
    ("GET", "/anomalies/evaluation"): "viewed model evaluation",
    ("POST", "/predict"): "ran a simulation",
    ("GET", "/audit"): "viewed audit log",
}


def describe_action(method: str, path: str) -> str:
    if (method, path) in ACTION_MAP:
        return ACTION_MAP[(method, path)]

    if method == "GET" and path.startswith("/days/"):
        date = path.replace("/days/", "")
        return f"viewed details for {date}"

    return f"{method} {path}"


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        path = str(request.url.path)
        if path.startswith("/docs") or path.startswith("/openapi") or path == "/favicon.ico":
            return response
        if request.method == "OPTIONS":
            return response

        user = "anonymous"
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            from app.auth import SECRET_KEY, ALGORITHM
            from jose import jwt, JWTError
            try:
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user = payload.get("sub", "anonymous")
            except (JWTError, IndexError):
                pass

        action = describe_action(request.method, path)

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user": user,
            "action": action,
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
        }
        audit_entries.append(entry)

        if len(audit_entries) > 1000:
            audit_entries.pop(0)

        return response


def get_audit_log() -> list:
    return list(reversed(audit_entries))
