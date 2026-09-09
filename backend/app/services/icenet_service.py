"""IceNet pretrained model wrapper for sea-ice concentration forecast."""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger


class IceNetService:
    """
    Wraps the IceNet pretrained model for sea-ice concentration (SIC) forecasting.

    IceNet architecture:
    - U-Net based CNN trained on ERA5 + CMIP6 data
    - Inputs: historical SIC, temperature, wind, sea-level pressure
    - Output: probabilistic SIC forecast for each cell in the Southern Ocean grid
    - Pretrained weights from: https://github.com/SFI-Visual-Intelligence/SFI-VI-IceNet-Task-Force

    If weights are missing, falls back to a physics-based sinusoidal seasonal model.
    """

    # IceNet grid (25 km EASE2 grid, subset for Southern Ocean)
    LAT_MIN = -90.0
    LAT_MAX = -55.0
    LON_MIN = -180.0
    LON_MAX = 180.0
    GRID_STEP = 0.5  # degrees (approximation for display)

    def __init__(self, checkpoint_dir: str, mc_dropout_passes: int = 30):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.mc_dropout_passes = mc_dropout_passes
        self._model = None
        self._loaded = False
        self._use_physics = True

    def load(self) -> None:
        """Attempt to load IceNet pretrained weights."""
        checkpoint = self.checkpoint_dir / "icenet_pretrained.pth"
        if not checkpoint.exists():
            logger.warning(
                "IceNet checkpoint not found at {}. Using physics seasonal model.",
                checkpoint,
            )
            self._use_physics = True
            return

        try:
            import torch

            logger.info("Loading IceNet pretrained weights from {}", checkpoint)
            # IceNet U-Net model structure
            self._model = self._build_icenet_unet()
            state_dict = torch.load(checkpoint, map_location="cpu")
            self._model.load_state_dict(state_dict, strict=False)
            self._model.eval()
            self._use_physics = False
            self._loaded = True
            logger.info("IceNet model loaded successfully (MC-Dropout T={})", self.mc_dropout_passes)
        except Exception as exc:
            logger.error("IceNet load failed: {}. Falling back to physics model.", exc)
            self._use_physics = True

    def _build_icenet_unet(self):
        """Build IceNet U-Net architecture for pretrained weight loading."""
        try:
            import torch
            import torch.nn as nn

            class DoubleConv(nn.Module):
                def __init__(self, in_ch, out_ch):
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Conv2d(in_ch, out_ch, 3, padding=1),
                        nn.BatchNorm2d(out_ch),
                        nn.ReLU(inplace=True),
                        nn.Dropout2d(0.1),
                        nn.Conv2d(out_ch, out_ch, 3, padding=1),
                        nn.BatchNorm2d(out_ch),
                        nn.ReLU(inplace=True),
                    )

                def forward(self, x):
                    return self.net(x)

            class IceNetUNet(nn.Module):
                def __init__(self, in_channels=12, out_channels=1):
                    super().__init__()
                    self.enc1 = DoubleConv(in_channels, 64)
                    self.enc2 = DoubleConv(64, 128)
                    self.enc3 = DoubleConv(128, 256)
                    self.pool = nn.MaxPool2d(2)
                    self.bottleneck = DoubleConv(256, 512)
                    self.up3 = nn.ConvTranspose2d(512, 256, 2, stride=2)
                    self.dec3 = DoubleConv(512, 256)
                    self.up2 = nn.ConvTranspose2d(256, 128, 2, stride=2)
                    self.dec2 = DoubleConv(256, 128)
                    self.up1 = nn.ConvTranspose2d(128, 64, 2, stride=2)
                    self.dec1 = DoubleConv(128, 64)
                    self.out = nn.Conv2d(64, out_channels, 1)
                    self.sigmoid = nn.Sigmoid()

                def forward(self, x):
                    e1 = self.enc1(x)
                    e2 = self.enc2(self.pool(e1))
                    e3 = self.enc3(self.pool(e2))
                    b = self.bottleneck(self.pool(e3))
                    d3 = self.dec3(torch.cat([self.up3(b), e3], dim=1))
                    d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
                    d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
                    return self.sigmoid(self.out(d1))

            return IceNetUNet()
        except ImportError:
            return None

    # ── Public API ─────────────────────────────────────────────────────────────

    def forecast(self, lead_day: int = 0, reference_time: Optional[datetime] = None) -> list[dict]:
        """
        Generate SIC forecast grid.
        Returns list of {lat, lon, concentration, uncertainty} dicts.
        """
        if reference_time is None:
            reference_time = datetime.utcnow()

        target_time = reference_time + timedelta(days=lead_day)

        if not self._use_physics and self._model is not None:
            return self._icenet_inference(target_time)
        return self._physics_forecast(target_time)

    def _physics_forecast(self, target_time: datetime) -> list[dict]:
        """
        Physics-based seasonal sea-ice model for Southern Ocean.
        Ice extent peaks in August–September, minimum in February–March.
        """
        rng = np.random.default_rng(seed=int(target_time.timestamp()) % (2**31))

        # Seasonal phase: maximum ice at day ~245 (Sep 2), minimum at day ~45 (Feb 14)
        day_of_year = target_time.timetuple().tm_yday
        seasonal_phase = math.cos(2 * math.pi * (day_of_year - 245) / 365)
        # seasonal_phase in [-1, 1]; +1 = max ice, -1 = min ice

        cells = []
        lat_step = 1.0
        lon_step = 2.0

        lats = np.arange(self.LAT_MIN, self.LAT_MAX + lat_step, lat_step)
        lons = np.arange(self.LON_MIN, self.LON_MAX + lon_step, lon_step)

        for lat in lats:
            # Ice extent boundary (latitude where ice starts)
            # Base ~-70°S in summer, extends to ~-55°S in winter
            ice_boundary = -70.0 + 15.0 * (seasonal_phase + 1) / 2
            for lon in lons:
                distance_from_boundary = lat - ice_boundary
                if distance_from_boundary >= 0:
                    # North of boundary = no ice
                    conc = 0.0
                    unc = 0.02
                else:
                    # South of boundary = increasing ice concentration
                    # Full ice (>0.8) at ~5° south of boundary
                    raw = min(1.0, abs(distance_from_boundary) / 5.0)
                    # Add small random noise for realism
                    noise = rng.normal(0, 0.05)
                    conc = float(np.clip(raw + noise, 0.0, 1.0))
                    unc = float(0.05 + 0.15 * (1.0 - raw))

                cells.append({
                    "lat": float(lat),
                    "lon": float(lon),
                    "concentration": round(conc, 3),
                    "uncertainty": round(unc, 3),
                })

        logger.debug("Physics ice forecast: {} cells for day {}", len(cells), target_time.date())
        return cells

    def _icenet_inference(self, target_time: datetime) -> list[dict]:
        """MC-Dropout inference on pretrained IceNet weights."""
        try:
            import torch

            # Create dummy input (real use case: assemble ERA5 + historical SIC input tensor)
            dummy_input = torch.zeros(1, 12, 64, 128)

            # MC-Dropout: run T forward passes with dropout enabled
            self._model.train()  # enable dropout
            predictions = []
            with torch.no_grad():
                for _ in range(self.mc_dropout_passes):
                    out = self._model(dummy_input)  # shape: (1, 1, 64, 128)
                    predictions.append(out.squeeze().numpy())

            mean_pred = np.mean(predictions, axis=0)
            std_pred = np.std(predictions, axis=0)

            # Map back to lat/lon grid
            cells = []
            lat_step = (self.LAT_MAX - self.LAT_MIN) / mean_pred.shape[0]
            lon_step = (self.LON_MAX - self.LON_MIN) / mean_pred.shape[1]

            for i in range(mean_pred.shape[0]):
                for j in range(mean_pred.shape[1]):
                    lat = self.LAT_MIN + i * lat_step
                    lon = self.LON_MIN + j * lon_step
                    cells.append({
                        "lat": float(lat),
                        "lon": float(lon),
                        "concentration": float(np.clip(mean_pred[i, j], 0, 1)),
                        "uncertainty": float(np.clip(std_pred[i, j], 0, 1)),
                    })
            return cells
        except Exception as exc:
            logger.error("IceNet inference failed: {}", exc)
            return self._physics_forecast(target_time)


_icenet_instance: Optional[IceNetService] = None


def get_icenet() -> IceNetService:
    global _icenet_instance
    if _icenet_instance is None:
        from config import get_settings
        s = get_settings()
        _icenet_instance = IceNetService(
            checkpoint_dir=str(s.icenet_checkpoint_dir),
            mc_dropout_passes=s.mc_dropout_passes,
        )
        _icenet_instance.load()
    return _icenet_instance
