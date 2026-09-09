"""Central configuration for IceNavigator backend."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost"

    # ── External API Keys ────────────────────────────────────
    cdsapi_url: str = "https://cds.climate.copernicus.eu/api/v2"
    cdsapi_key: str = ""
    earthdata_user: str = ""
    earthdata_pass: str = ""
    marinetraffic_api_key: str = ""
    sentinel_hub_client_id: str = ""
    sentinel_hub_client_secret: str = ""
    sentinel_hub_instance_id: str = ""
    cesium_ion_token: str = ""

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── Paths ────────────────────────────────────────────────
    model_cache_dir: str = "./checkpoints"
    data_dir: str = "./data"

    # ── Cache TTLs (seconds) ─────────────────────────────────
    ice_cache_ttl: int = 6 * 3600       # 6 hours
    iceberg_cache_ttl: int = 12 * 3600  # 12 hours
    ship_cache_ttl: int = 60            # 1 minute

    # ── Model settings ───────────────────────────────────────
    mc_dropout_passes: int = 30
    icenet_lead_times: int = 7  # forecast days

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def icenet_checkpoint_dir(self) -> Path:
        return Path(self.model_cache_dir) / "icenet"

    @property
    def drift_checkpoint_dir(self) -> Path:
        return Path(self.model_cache_dir) / "drift"

    @property
    def gebco_path(self) -> Path:
        return Path(self.data_dir) / "gebco.nc"

    @property
    def byu_iceberg_path(self) -> Path:
        return Path(self.data_dir) / "iceberg_tracks.csv"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
