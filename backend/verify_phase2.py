"""Phase 2 scientific engines end-to-end test."""
import sys
sys.path.insert(0, '.')

print("=== Phase 2: Scientific Engines Verification ===\n")

# 1. IceNet
print("[1] IceNet SIC Forecast")
from app.services.icenet_service import get_icenet
icenet = get_icenet()
# Test ingested grid path
cells = icenet.forecast(lead_day=0)
print(f"    lead_day=0 -> {len(cells)} SIC cells, source={'ingested' if icenet._ingested_grid else 'physics'}")
cells_3 = icenet.forecast(lead_day=3)
print(f"    lead_day=3 -> {len(cells_3)} SIC cells (physics fallback for future)")
sample = cells[:3]
for c in sample:
    print(f"    lat={c['lat']}, lon={c['lon']}, conc={c['concentration']:.3f}, unc={c['uncertainty']:.3f}")

# 2. DRIFT Service
print("\n[2] DRIFT Trajectory & MC-Dropout Ensemble")
from app.services.drift_service import get_drift
drift = get_drift()

# Test RK4 physics drift for iceberg A23A
traj = drift.predict_trajectory(
    lat=-75.24, lon=-25.10,
    heading_deg=15, velocity_ms=0.08,
    hours_ahead=72, dt_hours=6.0,
    fetch_live_wind=False
)
print(f"    A23A trajectory: {len(traj)} waypoints over 72h")
print(f"    T+0:  lat={traj[0]['lat']:.4f}, lon={traj[0]['lon']:.4f}")
print(f"    T+72: lat={traj[-1]['lat']:.4f}, lon={traj[-1]['lon']:.4f}, uncertainty={traj[-1]['uncertainty_radius_km']:.1f}km")

# MC-Dropout ensemble
ensemble = drift.mc_dropout_ensemble(
    lat=-75.24, lon=-25.10, heading_deg=15, velocity_ms=0.08,
    hours_ahead=48, n_samples=10
)
print(f"    MC-Dropout ensemble: {len(ensemble)} trajectories × {len(ensemble[0])} steps")

# Uncertainty cone
from app.services.uncertainty_service import compute_uncertainty_cone
cone = compute_uncertainty_cone(ensemble, n_sigma=2.0)
print(f"    Uncertainty cone: {len(cone)} timesteps, max_radius={max(c['radius_km'] for c in cone):.1f}km")

# ACC current estimation
u, v = drift._estimate_acc_current(-55.0, 0.0)
print(f"    ACC at 55S/0E: u={u}m/s (eastward), v={v}m/s")

# 3. Routing Service
print("\n[3] A* Routing Engine")
from app.services.routing_service import get_routing
routing = get_routing()

# Load state
from app.services.ingestion_service import get_ingestion
ing = get_ingestion()
sic_cells = ing.get_sic_cells()
icebergs  = ing.get_icebergs()
routing.update_ice_grid(sic_cells)
routing.update_icebergs(icebergs)
print(f"    Router loaded: {len(sic_cells)} SIC cells, {len(icebergs)} icebergs")

# Test iceberg spatial hash
dist = routing._nearest_iceberg_dist(-63.5, -55.2)
print(f"    Nearest iceberg to A76A base: {dist:.1f}km (should be ~0)")

# Route test: Punta Arenas → Palmer Station
result = routing.find_route(
    start_lat=-53.16, start_lon=-70.91,
    end_lat=-64.77, end_lon=-64.05,
    ship_type="ice_class_1a",
    min_depth_m=20.0,
    avoid_icebergs=True,
    max_iterations=3000,
)
print(f"    Punta Arenas -> Palmer: {result['distance_km']:.0f}km, ETA={result['eta_hours']:.1f}h")
print(f"    Risk: {result['risk_score']:.3f} (ice={result['risk_breakdown']['ice_risk']:.3f}, berg={result['risk_breakdown']['iceberg_risk']:.3f})")
print(f"    Fuel: {result['fuel_estimate_tons']:.1f}t HFO")
print(f"    Explanation: {result['explanation'][:100]}...")

# 4. AIS Service
print("\n[4] AIS Fleet (mock propagation)")
from app.services.ais_service import _ANTARCTIC_FLEET, _propagate_ship
ship = _propagate_ship(_ANTARCTIC_FLEET[0], hours_elapsed=6.0)
print(f"    {ship['name']}: lat={ship['lat']}, lon={ship['lon']}, speed={ship['speed_knots']}kn, history={len(ship['history'])} pts")

print("\n=== Phase 2 Verification PASSED ===")
