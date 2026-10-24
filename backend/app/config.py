"""Application settings loaded from environment."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def _get(key, default=""):
    return os.getenv(key, default)

class Settings:
    at_subscription_key = _get("AT_SUBSCRIPTION_KEY", "")
    at_vehicle_locations_url = _get("AT_VEHICLE_LOCATIONS_URL", "https://api.at.govt.nz/realtime/legacy/vehiclelocations")
    at_trip_updates_url = _get("AT_TRIP_UPDATES_URL", "https://api.at.govt.nz/realtime/legacy/tripupdates")
    at_service_alerts_url = _get("AT_SERVICE_ALERTS_URL", "https://api.at.govt.nz/realtime/legacy/servicealerts")
    at_gtfs_routes_url = _get("AT_GTFS_ROUTES_URL", "")

    gtfs_zip_url = _get("GTFS_ZIP_URL", "https://gtfs.at.govt.nz/gtfs.zip")
    gtfs_zip_path = _get("GTFS_ZIP_PATH", "./data/gtfs.zip")

    refresh_interval_seconds = int(_get("REFRESH_INTERVAL_SECONDS", "30"))
    host = _get("HOST", "127.0.0.1")
    port = int(_get("PORT", "8000"))
    frontend_origin = _get("FRONTEND_ORIGIN", "http://localhost:5173")

    @property
    def gtfs_zip(self):
        return Path(self.gtfs_zip_path)

settings = Settings()
