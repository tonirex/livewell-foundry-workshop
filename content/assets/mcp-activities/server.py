"""LiveWell activities MCP server + profile API (Lab 3 · Tools, MCP & Memory).

Two tools over MCP streamable HTTP at ``/mcp``:

* ``find_activities``  -- READ.  Search the synthetic community-activity catalogue
  (``content/data/activities.json``). Configure the Foundry MCP tool with *no approval* for it.
* ``register_interest`` -- WRITE. Record a resident's interest in one activity. Configure the Foundry
  MCP tool with *approval required* for it, so the coach must wait for a human "yes".

Plus the Navigator OpenAPI tool ``livewell_profile`` (spec at ``/openapi.json``):

* ``GET /profile/{resident_id}`` (operationId ``get_citizen_profile``) -- the signed-in resident's
  profile from ``content/data/citizens.json``. Only the session resident (``me`` or
  ``SESSION_RESIDENT_ID``) is served; any other id gets HTTP 403, so a prompt such as
  "show me RESIDENT_00062" fails at the tool as well as in the instructions.

Workshop-only: no authentication, synthetic data, registrations kept in memory (they vanish when the
container scales to zero). It never asks for or stores NRIC numbers, dates of birth or passwords.

Run locally:   python server.py            (listens on $PORT, default 80; use PORT=8000 locally)
Deploy:        azd deploy mcp-activities   (Container App ca-mcp-activities-<env>)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import threading
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

HERE = pathlib.Path(__file__).resolve().parent


def _data_path(name: str, env_var: str) -> pathlib.Path:
    # Container image: the JSON files are copied next to server.py by the azd prepackage hook.
    # Local run from the repo: fall back to the single source in content/data/.
    candidates = [
        pathlib.Path(os.environ[env_var]) if os.environ.get(env_var) else None,
        HERE / name,
        HERE.parent.parent / "data" / name,
    ]
    for path in candidates:
        if path and path.is_file():
            return path
    raise FileNotFoundError(f"{name} not found; set {env_var} or run from the repo")


CATALOGUE: dict[str, Any] = json.loads(_data_path("activities.json", "ACTIVITIES_PATH").read_text(encoding="utf-8"))
CITIZENS: dict[str, Any] = json.loads(_data_path("citizens.json", "CITIZENS_PATH").read_text(encoding="utf-8"))
SESSION_RESIDENT_ID: str = os.environ.get("SESSION_RESIDENT_ID") or CITIZENS["default_resident_id"]
ACTIVITIES: list[dict[str, Any]] = CATALOGUE["activities"]
CONDITION_VALUES: list[str] = CATALOGUE["condition_friendly_values"]
TIMES_OF_DAY = ("morning", "afternoon", "evening")
MAX_RESULTS = 8

_ALIASES = {
    "prediabetes": "pre-diabetes",
    "pre diabetes": "pre-diabetes",
    "diabetes": "pre-diabetes",
    "high blood sugar": "pre-diabetes",
    "elevated blood glucose": "pre-diabetes",
    "high blood pressure": "hypertension",
    "cholesterol": "high-cholesterol",
    "senior": "seniors",
    "elderly": "seniors",
    "beginner": "beginners",
}

mcp = FastMCP(
    "livewell-activities",
    instructions=(
        "Synthetic LiveWell community-activity catalogue for Singapore planning areas. "
        "find_activities is read-only. register_interest writes a registration and must only be "
        "called after the resident explicitly agrees."
    ),
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "80")),
    stateless_http=True,
)

_lock = threading.Lock()
_registrations: list[dict[str, Any]] = []


def _norm_condition(value: str) -> str:
    v = (value or "").strip().lower()
    return _ALIASES.get(v, v)


def _summary(a: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "activity_id", "name", "category", "programme", "venue", "planning_area", "region", "indoor",
        "hazy_day_ok", "day_of_week", "start_time", "time_of_day", "duration_min", "intensity",
        "condition_friendly", "cost_sgd", "healthpoints_on_attendance",
    )
    return {k: a[k] for k in keys if k in a}  # "programme" only on HPB programme intake sessions


@mcp.tool()
def find_activities(
    area: str,
    condition_friendly: str = "",
    indoor_only: bool = False,
    time_of_day: str = "",
) -> dict[str, Any]:
    """Find community healthy-living activities in a Singapore planning area or region.

    Results can include an HPB programme's intake session; those carry a "programme" field
    (for example "Diabetes Prevention").

    Args:
        area: Planning area (for example "Woodlands") or region ("North", "West", "Central",
            "East", "North-East").
        condition_friendly: Optional. One of pre-diabetes, hypertension, high-cholesterol, seniors,
            beginners. Leave empty for any.
        indoor_only: True to return only indoor, hazy-day-safe activities (use on hazy days).
        time_of_day: Optional. morning, afternoon or evening. Leave empty for any.
    """
    wanted = (area or "").strip().lower()
    condition = _norm_condition(condition_friendly)
    tod = (time_of_day or "").strip().lower()
    if condition and condition not in CONDITION_VALUES:
        return {"error": f"condition_friendly must be one of {CONDITION_VALUES} or empty", "activities": []}
    if tod and tod not in TIMES_OF_DAY:
        return {"error": f"time_of_day must be one of {list(TIMES_OF_DAY)} or empty", "activities": []}

    def matches(a: dict[str, Any], by: str) -> bool:
        if a[by].lower() != wanted:
            return False
        if condition and condition not in a["condition_friendly"]:
            return False
        if indoor_only and not (a["indoor"] and a["hazy_day_ok"]):
            return False
        return not tod or a["time_of_day"] == tod

    hits = [a for a in ACTIVITIES if matches(a, "planning_area")]
    matched_on = "planning_area"
    if not hits:
        hits = [a for a in ACTIVITIES if matches(a, "region")]
        matched_on = "region"
    if not hits and not any(wanted in (a["planning_area"].lower(), a["region"].lower()) for a in ACTIVITIES):
        areas = sorted({a["planning_area"] for a in ACTIVITIES})
        return {"error": f"unknown area {area!r}; try one of {areas}", "activities": []}
    return {
        "area": area,
        "matched_on": matched_on,
        "filters": {"condition_friendly": condition or None, "indoor_only": indoor_only, "time_of_day": tod or None},
        "count": len(hits),
        "activities": [_summary(a) for a in hits[:MAX_RESULTS]],
        "note": "Synthetic catalogue for the LiveWell workshop.",
    }


@mcp.tool()
def register_interest(activity_id: str, display_name: str) -> dict[str, Any]:
    """Register the resident's interest in one activity. WRITE action: call only after the resident
    has clearly said yes. Needs only the activity_id and the resident's first name -- never an NRIC,
    date of birth or password.

    Args:
        activity_id: The activity_id returned by find_activities (for example "ACT001").
        display_name: The resident's first name as they want the organiser to see it.
    """
    activity = next((a for a in ACTIVITIES if a["activity_id"] == (activity_id or "").strip().upper()), None)
    if activity is None:
        return {"status": "not_found", "error": f"no activity with id {activity_id!r}"}
    name = (display_name or "").strip()[:40] or "Resident"
    with _lock:
        registration_id = f"REG-{len(_registrations) + 1:04d}"
        record = {
            "registration_id": registration_id,
            "activity_id": activity["activity_id"],
            "activity_name": activity["name"],
            "venue": activity["venue"],
            "when": f'{activity["day_of_week"]} {activity["start_time"]}',
            "display_name": name,
            "registered_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        }
        _registrations.append(record)
    return {
        "status": "interest_registered",
        **record,
        "next_step": "The organiser confirms in the Healthy 365 app. No NRIC or password is ever needed.",
    }


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "activities": len(ACTIVITIES), "registrations": len(_registrations)})


def session_profile(resident_id: str) -> tuple[int, dict[str, Any]]:
    """Profile of the signed-in resident only; the resident_id itself is not echoed back."""
    rid = (resident_id or "").strip()
    if rid.lower() not in ("me", SESSION_RESIDENT_ID.lower()):
        return 403, {"error": "not_permitted",
                     "message": "Only the signed-in resident's own profile is available. Use resident_id 'me'."}
    citizen = next((c for c in CITIZENS["citizens"] if c["resident_id"] == SESSION_RESIDENT_ID), None)
    if citizen is None:
        return 404, {"error": "not_found", "message": "session resident missing from citizens.json"}
    return 200, {k: v for k, v in citizen.items() if k not in ("resident_id", "persona_note")}


@mcp.custom_route("/profile/{resident_id}", methods=["GET"])
async def profile(request: Request) -> JSONResponse:
    status, body = session_profile(request.path_params["resident_id"])
    return JSONResponse(body, status_code=status)


@mcp.custom_route("/openapi.json", methods=["GET"])
async def openapi(request: Request) -> JSONResponse:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return JSONResponse({
        "openapi": "3.0.3",
        "info": {"title": "LiveWell resident profile", "version": "1.0.0",
                 "description": "Synthetic resident_360 extract for the signed-in resident only (LiveWell workshop)."},
        "servers": [{"url": f"{proto}://{host}"}],
        "paths": {"/profile/{resident_id}": {"get": {
            "operationId": "get_citizen_profile",
            "summary": "Get the signed-in resident's profile",
            "description": ("Returns age band, planning area, region, screening risk, conditions, steps, MVPA, "
                            "sleep, programmes and the region's hazy flag for the resident using the coach. "
                            "Always pass resident_id = 'me'. Other residents are refused (HTTP 403)."),
            "parameters": [{"name": "resident_id", "in": "path", "required": True,
                            "description": "Always 'me' (the signed-in resident).",
                            "schema": {"type": "string", "enum": ["me"]}}],
            "responses": {
                "200": {"description": "Profile of the signed-in resident",
                        "content": {"application/json": {"schema": {"type": "object"}}}},
                "403": {"description": "Another resident was requested"},
            },
        }}},
    })


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
