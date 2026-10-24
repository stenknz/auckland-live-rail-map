"""FastAPI application."""
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .gtfs import gtfs
from .realtime import realtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    gtfs.load()
    yield


app = FastAPI(title="Auckland Live Rail Map", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _shape_route_map() -> Dict[str, str]:
    m: Dict[str, str] = {}
    for t in gtfs.trips.values():
        if t.get("shape_id"):
            m[t["shape_id"]] = t["route_id"]
    return m


@app.get("/health")
def health():
    return {"status": "ok", "gtfs_loaded": gtfs.loaded, "gtfs_error": gtfs.error}


@app.get("/api/static")
def static_network():
    if not gtfs.loaded:
        raise HTTPException(503, gtfs.error or "GTFS not loaded")
    return {
        "routes": gtfs.routes,
        "stops": gtfs.stops,
        "shapes": gtfs.shapes,
        "shape_routes": _shape_route_map(),
    }


def _is_rail_route(route_id: str | None) -> bool:
    if not gtfs.rail_route_ids:
        return True
    return route_id in gtfs.rail_route_ids


@app.get("/api/vehicles")
def vehicles():
    try:
        data = realtime.fetch_vehicles()
    except Exception as exc:
        if realtime.vehicles_cache.data is not None:
            data = realtime.vehicles_cache.data
        else:
            raise HTTPException(503, str(exc))
    filtered = []
    for v in data.get("vehicles", []):
        route_id = v.get("route_id")
        if route_id is None and v.get("trip_id"):
            route_id = gtfs.route_for_trip(v["trip_id"])
            v["route_id"] = route_id
        if not _is_rail_route(route_id):
            continue
        filtered.append(v)
    data["vehicles"] = filtered
    data["stale"] = realtime.vehicles_cache.stale
    data["error"] = realtime.vehicles_cache.error
    data["last_update"] = realtime.vehicles_cache.fetched_at
    return data


@app.get("/api/trip-updates")
def trip_updates():
    try:
        data = realtime.fetch_trip_updates()
    except Exception as exc:
        if realtime.trips_cache.data is not None:
            data = realtime.trips_cache.data
        else:
            raise HTTPException(503, str(exc))
    data["stale"] = realtime.trips_cache.stale
    data["error"] = realtime.trips_cache.error
    data["last_update"] = realtime.trips_cache.fetched_at
    return data


@app.get("/api/alerts")
def alerts():
    try:
        data = realtime.fetch_alerts()
    except Exception as exc:
        if realtime.alerts_cache.data is not None:
            data = realtime.alerts_cache.data
        else:
            raise HTTPException(503, str(exc))
    rail_stops = {s["stop_id"] for s in gtfs.stops}
    filtered = []
    for a in data.get("alerts", []):
        relevant = False
        for ie in a.get("informed", []):
            if ie.get("route_id") in gtfs.rail_route_ids:
                relevant = True
                break
            if ie.get("stop_id") in rail_stops:
                relevant = True
                break
        if not a.get("informed"):
            relevant = True
        if relevant:
            filtered.append(a)
    data["alerts"] = filtered
    data["stale"] = realtime.alerts_cache.stale
    data["error"] = realtime.alerts_cache.error
    data["last_update"] = realtime.alerts_cache.fetched_at
    return data


def _parse_gtfs_time(s: str, base_date) -> datetime:
    h, m, sec = (int(x) for x in s.split(":"))
    days = h // 24
    h = h % 24
    t = datetime(base_date.year, base_date.month, base_date.day, h, m, sec)
    return t + timedelta(days=days)


@app.get("/api/arrivals/{stop_id}")
def arrivals(stop_id: str):
    if not gtfs.loaded:
        raise HTTPException(503, gtfs.error or "GTFS not loaded")

    today = datetime.now().strftime("%Y%m%d")
    active_services = gtfs.active_service_ids(today)
    now = datetime.now()
    base_date = now.date()

    scheduled = []
    for st in gtfs.stop_times:
        if st["stop_id"] != stop_id:
            continue
        trip = gtfs.trips.get(st["trip_id"])
        if not trip:
            continue
        if trip.get("service_id") not in active_services:
            continue
        arr_str = st.get("arrival_time") or st.get("departure_time")
        if not arr_str:
            continue
        try:
            sched_dt = _parse_gtfs_time(arr_str, base_date)
        except Exception:
            continue
        if sched_dt < now - timedelta(minutes=2):
            # maybe next day already handled by >24; skip past
            continue
        route_id = trip["route_id"]
        route = next((r for r in gtfs.routes if r["route_id"] == route_id), None)
        scheduled.append(
            {
                "trip_id": trip["trip_id"],
                "route_id": route_id,
                "route_color": route["color"] if route else "888888",
                "route_short_name": route["short_name"] if route else "",
                "headsign": trip.get("headsign", ""),
                "scheduled_time": sched_dt.isoformat(),
                "platform": st.get("stop_id"),
            }
        )

    # realtime trip updates
    try:
        tu_data = realtime.fetch_trip_updates()
    except Exception:
        tu_data = realtime.trips_cache.data
    realtime_by_trip: Dict[str, Any] = {}
    if tu_data:
        for t in tu_data.get("trips", []):
            matching = None
            for su in t.get("stop_updates", []):
                if su.get("stop_id") == stop_id:
                    matching = su
                    break
            realtime_by_trip[t["trip_id"]] = (t, matching)

    results: List[Dict[str, Any]] = []
    seen = set()
    for s in scheduled:
        tid = s["trip_id"]
        seen.add(tid)
        rt = realtime_by_trip.get(tid)
        if rt:
            t, su = rt
            arr = (su.get("arrival") if su else None) or {}
            trip_delay = t.get("delay")
            try:
                trip_delay = int(trip_delay) if trip_delay is not None else 0
            except (ValueError, TypeError):
                trip_delay = 0
            est_time = None
            delay = arr.get("delay")
            if delay is None:
                delay = trip_delay
            if arr.get("time"):
                est_time = datetime.fromtimestamp(arr["time"]).isoformat()
            else:
                try:
                    sched = datetime.fromisoformat(s["scheduled_time"])
                    est_time = (sched + timedelta(seconds=trip_delay)).isoformat()
                except Exception:
                    est_time = s["scheduled_time"]
            cancelled = False
            results.append(
                {
                    **s,
                    "realtime": True,
                    "estimated_time": est_time or s["scheduled_time"],
                    "delay_seconds": delay,
                    "cancelled": cancelled,
                }
            )
        else:
            results.append(
                {
                    **s,
                    "realtime": False,
                    "estimated_time": s["scheduled_time"],
                    "delay_seconds": None,
                    "cancelled": False,
                }
            )

    # realtime-only trips
    for tid, (t, su) in realtime_by_trip.items():
        if tid in seen:
            continue
        arr = (su.get("arrival") if su else None) or {}
        est_time = None
        if arr.get("time"):
            est_time = datetime.fromtimestamp(arr["time"])
        if est_time is None or est_time < now - timedelta(minutes=2):
            continue
        route_id = t.get("route_id") or gtfs.route_for_trip(tid)
        route = next((r for r in gtfs.routes if r["route_id"] == route_id), None)
        results.append(
            {
                "trip_id": tid,
                "route_id": route_id,
                "route_color": route["color"] if route else "888888",
                "route_short_name": route["short_name"] if route else "",
                "headsign": "",
                "scheduled_time": None,
                "realtime": True,
                "estimated_time": est_time.isoformat(),
                "delay_seconds": arr.get("delay"),
                "cancelled": False,
                "platform": None,
            }
        )

    def sort_key(x):
        t = x.get("estimated_time") or x.get("scheduled_time")
        try:
            return datetime.fromisoformat(t)
        except Exception:
            return now

    results.sort(key=sort_key)
    results = results[:20]

    return {
        "stop_id": stop_id,
        "stop_name": gtfs.stop_name(stop_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "arrivals": results,
        "stale": realtime.trips_cache.stale,
        "error": realtime.trips_cache.error,
        "last_update": realtime.trips_cache.fetched_at,
    }


@app.get("/api/status")
def status():
    return {
        "gtfs": {"loaded": gtfs.loaded, "error": gtfs.error, "stops": len(gtfs.stops), "routes": len(gtfs.routes)},
        "vehicles": {
            "last_update": realtime.vehicles_cache.fetched_at,
            "age_seconds": realtime.vehicles_cache.age(),
            "stale": realtime.vehicles_cache.stale,
            "error": realtime.vehicles_cache.error,
        },
        "trips": {
            "last_update": realtime.trips_cache.fetched_at,
            "age_seconds": realtime.trips_cache.age(),
            "stale": realtime.trips_cache.stale,
            "error": realtime.trips_cache.error,
        },
        "alerts": {
            "last_update": realtime.alerts_cache.fetched_at,
            "age_seconds": realtime.alerts_cache.age(),
            "stale": realtime.alerts_cache.stale,
            "error": realtime.alerts_cache.error,
        },
        "server_time": datetime.now(timezone.utc).isoformat(),
    }
