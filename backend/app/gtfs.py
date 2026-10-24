"""Static GTFS parsing for Auckland rail."""
import csv
import io
import zipfile
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict

from .config import settings


def _read_csv(zf: zipfile.ZipFile, name: str) -> List[Dict[str, str]]:
    with zf.open(name) as f:
        raw = f.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(raw)))


class GtfsData:
    def __init__(self) -> None:
        self.routes: List[Dict[str, Any]] = []
        self.rail_route_ids: set = set()
        self.stops: List[Dict[str, Any]] = []
        self.rail_stop_ids: set = set()
        self.shapes: Dict[str, List[List[float]]] = {}
        self.trips: Dict[str, Dict[str, Any]] = {}
        self.stop_times: List[Dict[str, Any]] = []
        self.calendar: Dict[str, Dict[str, str]] = {}
        self.calendar_dates: List[Dict[str, str]] = []
        self.loaded: bool = False
        self.error: str | None = None

    def load(self, zip_path=None) -> None:
        path = zip_path or settings.gtfs_zip
        try:
            if not path.exists():
                import httpx

                with httpx.Client(timeout=120) as client:
                    r = client.get(settings.gtfs_zip_url)
                    r.raise_for_status()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(r.content)
            zf = zipfile.ZipFile(path)
        except Exception as exc:
            self.error = str(exc)
            return

        routes_raw = _read_csv(zf, "routes.txt")
        trips_raw = _read_csv(zf, "trips.txt")
        stops_raw = _read_csv(zf, "stops.txt")
        shapes_raw = _read_csv(zf, "shapes.txt")
        stop_times_raw = _read_csv(zf, "stop_times.txt")
        calendar_raw = _read_csv(zf, "calendar.txt")
        calendar_dates_raw = _read_csv(zf, "calendar_dates.txt")

        for r in routes_raw:
            if r.get("route_type") == "2":
                self.rail_route_ids.add(r["route_id"])
                self.routes.append(
                    {
                        "route_id": r["route_id"],
                        "short_name": r.get("route_short_name", ""),
                        "long_name": r.get("route_long_name", ""),
                        "color": r.get("route_color") or "888888",
                        "text_color": r.get("route_text_color") or "FFFFFF",
                    }
                )

        rail_trip_ids = set()
        for t in trips_raw:
            if t["route_id"] in self.rail_route_ids:
                self.trips[t["trip_id"]] = {
                    "trip_id": t["trip_id"],
                    "route_id": t["route_id"],
                    "shape_id": t.get("shape_id") or None,
                    "headsign": t.get("trip_headsign") or "",
                    "direction_id": t.get("direction_id"),
                    "service_id": t.get("service_id"),
                }
                rail_trip_ids.add(t["trip_id"])

        for st in stop_times_raw:
            if st["trip_id"] in rail_trip_ids:
                self.rail_stop_ids.add(st["stop_id"])

        for s in stops_raw:
            if s["stop_id"] in self.rail_stop_ids:
                try:
                    lat = float(s["stop_lat"])
                    lon = float(s["stop_lon"])
                except (ValueError, TypeError):
                    continue
                self.stops.append(
                    {
                        "stop_id": s["stop_id"],
                        "name": s.get("stop_name", ""),
                        "lat": lat,
                        "lon": lon,
                        "platform": s.get("platform_code"),
                    }
                )

        rail_shape_ids = {t["shape_id"] for t in self.trips.values() if t["shape_id"]}
        shape_points: Dict[str, List[tuple]] = defaultdict(list)
        for s in shapes_raw:
            sid = s["shape_id"]
            if sid not in rail_shape_ids:
                continue
            try:
                seq = int(s["shape_pt_sequence"])
                lat = float(s["shape_pt_lat"])
                lon = float(s["shape_pt_lon"])
            except (ValueError, TypeError):
                continue
            shape_points[sid].append((seq, lat, lon))
        for sid, pts in shape_points.items():
            pts.sort(key=lambda x: x[0])
            self.shapes[sid] = [[p[1], p[2]] for p in pts]

        for c in calendar_raw:
            self.calendar[c["service_id"]] = c
        self.calendar_dates = calendar_dates_raw

        self.stop_times = [st for st in stop_times_raw if st["trip_id"] in rail_trip_ids]

        self.loaded = True
        self.error = None

    def active_service_ids(self, date_str: str) -> set:
        import datetime

        d = datetime.datetime.strptime(date_str, "%Y%m%d").date()
        weekday = d.strftime("%A").lower()
        active = set()
        for sid, c in self.calendar.items():
            start = c.get("start_date", "")
            end = c.get("end_date", "")
            if start and end and start <= date_str <= end:
                if c.get(weekday, "0") == "1":
                    active.add(sid)
        for cd in self.calendar_dates:
            if cd.get("date") == date_str:
                sid = cd["service_id"]
                et = cd.get("exception_type")
                if et == "1":
                    active.add(sid)
                elif et == "2":
                    active.discard(sid)
        return active

    def route_for_trip(self, trip_id: str):
        t = self.trips.get(trip_id)
        return t["route_id"] if t else None

    def stop_name(self, stop_id: str):
        for s in self.stops:
            if s["stop_id"] == stop_id:
                return s["name"]
        return None


gtfs = GtfsData()
