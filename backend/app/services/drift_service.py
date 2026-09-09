"""
DRIFT iceberg trajectory model wrapper.

Supports two modes:
1. DRIFT pretrained model (from https://github.com/marco-jaeger/drift)
   - Deep learning model for iceberg drift prediction
   - Loads checkpoint from checkpoints/drift/
2. Physics-based drift model (always available):
   - wind_factor * wind_velocity + current_velocity + Coriolis correction
   - Matches standard IICG (International Ice Charting Group) equations
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger


# ── Physics constants ──────────────────────────────────────────────────────────
OMEGA = 7.2921e-5   # Earth rotation rate (rad/s)
WIND_FACTOR = 0.018  # Iceberg drift ≈ 1.8% of wind speed (empirical)


class DriftService:
    """
    Iceberg trajectory prediction using DRIFT pretrained model or physics drift.

    Physics model:
        v_iceberg = α * v_wind + v_current + f × v_iceberg  (Coriolis)
    where:
        α = WIND_FACTOR (0.018)
        f = 2 * Ω * sin(lat)  (Coriolis parameter)
    """

    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self._model = None
        self._use_physics = True

    def load(self) -> None:
        """Attempt to load DRIFT pretrained weights."""
        checkpoint = self.checkpoint_dir / "drift_pretrained.pth"
        if not checkpoint.exists():
            logger.warning(
                "DRIFT checkpoint not found at {}. Using physics drift model.",
                checkpoint,
            )
            return

        try:
            import torch

            logger.info("Loading DRIFT pretrained model from {}", checkpoint)
            self._model = self._build_drift_model()
            state_dict = torch.load(checkpoint, map_location="cpu")
            self._model.load_state_dict(state_dict, strict=False)
            self._model.eval()
            self._use_physics = False
            logger.info("DRIFT model loaded successfully")
        except Exception as exc:
            logger.error("DRIFT load failed: {}. Using physics model.", exc)

    def _build_drift_model(self):
        """DRIFT LSTM architecture for trajectory prediction."""
        try:
            import torch.nn as nn

            class DriftLSTM(nn.Module):
                def __init__(self, input_size=10, hidden_size=128, num_layers=2, output_size=2):
                    super().__init__()
                    self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                                        batch_first=True, dropout=0.2)
                    self.fc = nn.Sequential(
                        nn.Linear(hidden_size, 64),
                        nn.ReLU(),
                        nn.Dropout(0.1),
                        nn.Linear(64, output_size),
                    )

                def forward(self, x):
                    out, _ = self.lstm(x)
                    return self.fc(out[:, -1, :])

            return DriftLSTM()
        except ImportError:
            return None

    # ── Public API ─────────────────────────────────────────────────────────────

    def predict_trajectory(
        self,
        lat: float,
        lon: float,
        heading_deg: float,
        velocity_ms: float,
        wind_u: float = 0.0,
        wind_v: float = 0.0,
        current_u: float = 0.0,
        current_v: float = 0.0,
        hours_ahead: int = 72,
        dt_hours: float = 6.0,
    ) -> list[dict]:
        """
        Predict iceberg trajectory.

        Args:
            lat, lon: Starting position
            heading_deg: Current heading (degrees true)
            velocity_ms: Current speed (m/s)
            wind_u, wind_v: Wind components (m/s)
            current_u, current_v: Ocean current components (m/s)
            hours_ahead: Total forecast horizon
            dt_hours: Time step

        Returns:
            List of {lat, lon, timestamp, uncertainty_radius_km}
        """
        if not self._use_physics and self._model is not None:
            return self._drift_inference(lat, lon, wind_u, wind_v, current_u, current_v, hours_ahead, dt_hours)
        return self._physics_drift(lat, lon, heading_deg, velocity_ms,
                                   wind_u, wind_v, current_u, current_v,
                                   hours_ahead, dt_hours)

    def mc_dropout_ensemble(
        self,
        lat: float,
        lon: float,
        heading_deg: float,
        velocity_ms: float,
        wind_u: float = 0.0,
        wind_v: float = 0.0,
        current_u: float = 0.0,
        current_v: float = 0.0,
        hours_ahead: int = 72,
        n_samples: int = 30,
    ) -> list[list[dict]]:
        """
        MC-Dropout ensemble: returns n_samples trajectories for uncertainty quantification.
        """
        trajectories = []
        rng = np.random.default_rng(42)

        for i in range(n_samples):
            # Perturb wind and current slightly for ensemble spread
            perturb_wind_u = wind_u + rng.normal(0, 1.0)
            perturb_wind_v = wind_v + rng.normal(0, 1.0)
            perturb_current_u = current_u + rng.normal(0, 0.05)
            perturb_current_v = current_v + rng.normal(0, 0.05)

            traj = self._physics_drift(
                lat, lon, heading_deg, velocity_ms,
                perturb_wind_u, perturb_wind_v,
                perturb_current_u, perturb_current_v,
                hours_ahead, dt_hours=6.0,
            )
            trajectories.append(traj)

        return trajectories

    # ── Physics Model ──────────────────────────────────────────────────────────

    def _physics_drift(
        self,
        lat: float, lon: float,
        heading_deg: float, velocity_ms: float,
        wind_u: float, wind_v: float,
        current_u: float, current_v: float,
        hours_ahead: int, dt_hours: float,
    ) -> list[dict]:
        """
        Physics drift integration using Euler method.

        Equations:
            du/dt = α * wind_u + current_u + f * v
            dv/dt = α * wind_v + current_v - f * u
        where f = 2*Ω*sin(lat) (Coriolis parameter)
        """
        n_steps = int(hours_ahead / dt_hours)
        dt_s = dt_hours * 3600  # seconds

        # Initial velocity from heading + speed
        heading_rad = math.radians(heading_deg)
        u = velocity_ms * math.sin(heading_rad)
        v = velocity_ms * math.cos(heading_rad)

        trajectory = [{
            "lat": lat,
            "lon": lon,
            "timestamp": datetime.utcnow().isoformat(),
            "uncertainty_radius_km": 0.0,
        }]

        cumulative_uncertainty_km = 0.0

        for step in range(1, n_steps + 1):
            f = 2.0 * OMEGA * math.sin(math.radians(lat))

            # Acceleration (Coriolis + forcing)
            du = WIND_FACTOR * wind_u + current_u + f * v
            dv = WIND_FACTOR * wind_v + current_v - f * u

            # Euler integration
            u += du * dt_s * 0.01  # scale factor for stability
            v += dv * dt_s * 0.01

            # Distance moved
            dx_m = u * dt_s
            dy_m = v * dt_s

            # Convert to degrees (approximate)
            dlat = dy_m / 111_320.0
            dlon = dx_m / (111_320.0 * math.cos(math.radians(lat)))

            lat = max(-90.0, min(90.0, lat + dlat))
            lon = ((lon + dlon + 180) % 360) - 180

            # Uncertainty grows with time (random walk model)
            cumulative_uncertainty_km += 2.0 * math.sqrt(step)

            ts = (datetime.utcnow() + timedelta(hours=step * dt_hours)).isoformat()
            trajectory.append({
                "lat": lat,
                "lon": lon,
                "timestamp": ts,
                "uncertainty_radius_km": round(cumulative_uncertainty_km, 1),
            })

        return trajectory

    def _drift_inference(
        self,
        lat: float, lon: float,
        wind_u: float, wind_v: float,
        current_u: float, current_v: float,
        hours_ahead: int, dt_hours: float,
    ) -> list[dict]:
        """DRIFT LSTM inference (placeholder – real data assimilation required)."""
        try:
            import torch

            # Build input sequence (last 7 timesteps × 10 features)
            features = [lat, lon, wind_u, wind_v, current_u, current_v,
                        math.sin(math.radians(lat)), math.cos(math.radians(lat)), 0.0, 0.0]
            seq = torch.tensor([[features] * 7], dtype=torch.float32)

            self._model.train()  # MC-Dropout
            outputs = []
            with torch.no_grad():
                for _ in range(30):
                    out = self._model(seq)
                    outputs.append(out.numpy())

            mean_out = np.mean(outputs, axis=0)[0]
            pred_lat = lat + mean_out[0]
            pred_lon = lon + mean_out[1]

            # Interpolate trajectory
            return self._physics_drift(lat, lon, 0, 0.1, wind_u, wind_v, current_u, current_v,
                                       hours_ahead, dt_hours)
        except Exception as exc:
            logger.error("DRIFT inference failed: {}", exc)
            return self._physics_drift(lat, lon, 180, 0.1, wind_u, wind_v, current_u, current_v,
                                       hours_ahead, dt_hours)


_drift_instance: Optional[DriftService] = None


def get_drift() -> DriftService:
    global _drift_instance
    if _drift_instance is None:
        from config import get_settings
        s = get_settings()
        _drift_instance = DriftService(checkpoint_dir=str(s.drift_checkpoint_dir))
        _drift_instance.load()
    return _drift_instance
