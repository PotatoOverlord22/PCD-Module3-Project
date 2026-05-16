"""Role-based data redaction for privacy-by-design.

The caregiver role intentionally cannot see activity in sensitive rooms
(default: BATHROOM). Redaction happens server-side BEFORE the response
is serialized — clients cannot bypass it via DevTools or direct API
calls.

The redacted room names are still returned in a ``redacted_rooms`` list so
the UI can render a "🔒 hidden for privacy" placeholder in their place.
"""

from app.config import PRIVATE_ROOMS_FOR_CAREGIVER


def _redacted_rooms_for(role: str) -> set[str]:
    if role == "admin":
        return set()
    return set(PRIVATE_ROOMS_FOR_CAREGIVER)


def redact_day(day: dict | None, role: str) -> dict | None:
    """Return a copy of *day* with private rooms stripped out for the given role."""
    if day is None:
        return None
    hidden = _redacted_rooms_for(role)
    if not hidden:
        return day
    rooms = day.get("rooms", {}) or {}
    visible = {name: info for name, info in rooms.items() if name not in hidden}
    redacted = [name for name in rooms.keys() if name in hidden]
    return {**day, "rooms": visible, "redacted_rooms": redacted}


def redact_days(days: list[dict], role: str) -> list[dict]:
    return [redact_day(d, role) for d in days]


def redact_predict_response(response: dict, role: str) -> dict:
    """Mirror of redact_day for the /predict response shape."""
    hidden = _redacted_rooms_for(role)
    if not hidden:
        return response
    rooms = response.get("rooms", {}) or {}
    visible = {name: info for name, info in rooms.items() if name not in hidden}
    redacted = [name for name in rooms.keys() if name in hidden]
    return {**response, "rooms": visible, "redacted_rooms": redacted}
