"""Realtime feed fetching and parsing (AT legacy JSON feeds)."""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .config import settings


class RealtimeCache:
    def __init__(self) -> None:
        self.data: Any = None
        self.fetched_at: Optional[float] = None
        self.error: Optional[str] = None
        self.stale: bool = False

    def set(self, data: Any, error: Optional[str] = None, stale: bool = False) -> None:
        if data is not None:
            self.data = data
            self.fetched_at = time.time()
        self.error = error
        self.stale = stale

    def age(self) -> Optional[float]:
        if self.fetched_at is None:
            return None
        return time.time() - self.fetched_at


class RealtimeClient:
    def __init__(self) -> None:
        self.vehicles_cache = RealtimeCache()
        self.trips_cache = RealtimeCache()
        self.alerts_cache = RealtimeCache()

    def _headers(self) -> Dict[str, str]:
        h = {}
        if settings.at_subscription_key and settings.at_subscription_key != "CHANGEME":
            h["Ocp-Apim-Subscription-Key"] = settings.at_subscription_key
        return h

    def _fetch_json(self, url: str) -> dict:
        last_exc = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=30) as client:
                    r = client.get(url, headers=self._headers())
                    if r.status_code == 429 or r.status_code >= 500:
                        raise httpx.HTTPStatusError(
                            f"status {r.status_code}", request=r.request, response=r
                        )
                    r.raise_for_status()
                    return r.json()
            except Exception as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
        raise last_exc

    def _configured(self) -> bool:
        return bool(settings.at_subscription_key) and settings.at_subscription_key != "CHANGEME"

    def fetch_vehicles(self) -> Dict[str, Any]:
        if not self._configured():
            data = {"generated_at": None, "source_timestamp": None, "vehicles": []}
            self.vehicles_cache.set(data, error="AT_SUBSCRIPTION_KEY not configured", stale=False)
            return self.vehicles_cache.data
        try:
            payload = self._fetch_json(settings.at_vehicle_locations_url)
            resp = payload.get("response", {}) or {}
            entities = resp.get("entity", []) or []
            vehicles = []
            for ent in entities:
                v = ent.get("vehicle")
                if not v:
                    continue
                pos = v.get("position") or {}
                lat = pos.get("latitude")
                lon = pos.get("longitude")
                if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                    continue
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    continue
                if lat == 0 and lon == 0:
                    continue
                bearing = pos.get("bearing")
                try:
                    bearing = float(bearing) if bearing is not None else None
                except (ValueError, TypeError):
                    bearing = None
                ts = v.get("timestamp")
                try:
                    ts = int(ts) if ts is not None else None
                except (ValueError, TypeError):
                    ts = None
                vehicle_info = v.get("vehicle") or {}
                trip = v.get("trip") or {}
                vehicles.append(
                    {
                        "id": ent.get("id") or vehicle_info.get("id") or "unknown",
                        "vehicle_id": vehicle_info.get("id") or ent.get("id") or "unknown",
                        "vehicle_label": vehicle_info.get("label") or None,
                        "route_id": trip.get("route_id") or None,
                        "trip_id": trip.get("trip_id") or None,
                        "latitude": lat,
                        "longitude": lon,
                        "bearing": bearing,
                        "timestamp": ts,
                        "age_seconds": (int(time.time()) - ts) if ts else None,
                    }
                )
            header = resp.get("header") or {}
            st = header.get("timestamp")
            try:
                st = int(st) if st is not None else None
            except (ValueError, TypeError):
                st = None
            data = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_timestamp": st,
                "vehicles": vehicles,
            }
            self.vehicles_cache.set(data)
            return data
        except Exception as exc:
            if self.vehicles_cache.data is not None:
                self.vehicles_cache.set(None, error=str(exc), stale=True)
                return self.vehicles_cache.data
            self.vehicles_cache.set(None, error=str(exc), stale=False)
            raise

    def fetch_trip_updates(self) -> Dict[str, Any]:
        if not self._configured():
            data = {"generated_at": None, "source_timestamp": None, "trips": []}
            self.trips_cache.set(data, error="AT_SUBSCRIPTION_KEY not configured", stale=False)
            return self.trips_cache.data
        try:
            payload = self._fetch_json(settings.at_trip_updates_url)
            resp = payload.get("response", {}) or {}
            entities = resp.get("entity", []) or []
            trips = []
            for ent in entities:
                tu = ent.get("trip_update")
                if not tu:
                    continue
                trip = tu.get("trip") or {}
                stu = tu.get("stop_time_update")
                if isinstance(stu, dict):
                    stu = [stu]
                stops = []
                for s in (stu or []):
                    arr = s.get("arrival")
                    dep = s.get("departure")
                    stops.append(
                        {
                            "stop_id": s.get("stop_id"),
                            "arrival": (
                                {"time": arr.get("time"), "delay": arr.get("delay")}
                                if isinstance(arr, dict) else None
                            ),
                            "departure": (
                                {"time": dep.get("time"), "delay": dep.get("delay")}
                                if isinstance(dep, dict) else None
                            ),
                        }
                    )
                trips.append(
                    {
                        "id": ent.get("id"),
                        "trip_id": trip.get("trip_id") or None,
                        "route_id": trip.get("route_id") or None,
                        "start_time": trip.get("start_time") or None,
                        "start_date": trip.get("start_date") or None,
                        "timestamp": tu.get("timestamp"),
                        "delay": tu.get("delay"),
                        "stop_updates": stops,
                    }
                )
            header = resp.get("header") or {}
            st = header.get("timestamp")
            try:
                st = int(st) if st is not None else None
            except (ValueError, TypeError):
                st = None
            data = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_timestamp": st,
                "trips": trips,
            }
            self.trips_cache.set(data)
            return data
        except Exception as exc:
            if self.trips_cache.data is not None:
                self.trips_cache.set(None, error=str(exc), stale=True)
                return self.trips_cache.data
            self.trips_cache.set(None, error=str(exc), stale=False)
            raise

    def fetch_alerts(self) -> Dict[str, Any]:
        if not self._configured():
            data = {"generated_at": None, "source_timestamp": None, "alerts": []}
            self.alerts_cache.set(data, error="AT_SUBSCRIPTION_KEY not configured", stale=False)
            return self.alerts_cache.data
        try:
            payload = self._fetch_json(settings.at_service_alerts_url)
            resp = payload.get("response", {}) or {}
            entities = resp.get("entity", []) or []
            alerts = []
            for ent in entities:
                a = ent.get("alert")
                if not a:
                    continue
                ht = a.get("header_text") or {}
                dt = a.get("description_text") or {}
                header = None
                if ht.get("translation"):
                    header = ht["translation"][0].get("text")
                desc = None
                if dt.get("translation"):
                    desc = dt["translation"][0].get("text")
                informed = []
                for ie in a.get("informed_entity", []) or []:
                    informed.append(
                        {
                            "route_id": ie.get("route_id"),
                            "stop_id": ie.get("stop_id"),
                            "agency_id": ie.get("agency_id"),
                        }
                    )
                periods = []
                for ap in a.get("active_period", []) or []:
                    periods.append({"start": ap.get("start"), "end": ap.get("end")})
                alerts.append(
                    {
                        "id": ent.get("id"),
                        "header": header,
                        "description": desc,
                        "informed": informed,
                        "periods": periods,
                        "cause": a.get("cause"),
                        "effect": a.get("effect"),
                    }
                )
            header = resp.get("header") or {}
            st = header.get("timestamp")
            try:
                st = int(st) if st is not None else None
            except (ValueError, TypeError):
                st = None
            data = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_timestamp": st,
                "alerts": alerts,
            }
            self.alerts_cache.set(data)
            return data
        except Exception as exc:
            if self.alerts_cache.data is not None:
                self.alerts_cache.set(None, error=str(exc), stale=True)
                return self.alerts_cache.data
            self.alerts_cache.set(None, error=str(exc), stale=False)
            raise


realtime = RealtimeClient()
