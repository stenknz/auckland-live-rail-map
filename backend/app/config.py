"""Application settings loaded from environment."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    at_subscription_key: str = ""
    at_vehicle_locations_url: str = "https://api.at.govt.nz/realtime/legacy/vehiclelocations"
    at_trip_updates_url: str = "https://api.at.govt.nz/realtime/legacy/tripupdates"
    at_service_alerts_url: str = "https://api.at.govt.nz/realtime/legacy/servicealerts"
    at_gtfs_routes_url: str = ""

    gtfs_zip_url: str = "https://gtfs.at.govt.nz/gtfs.zip"
    gtfs_zip_path: str = "./data/gtfs.zip"

    refresh_interval_seconds: int = 30
    host: str = "127.0.0.1"
    port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    @property
    def gtfs_zip(self) -> Path:
        return Path(self.gtfs_zip_path)


settings = Settings()
