from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


TELEMETRY_FIELDS: List[str] = [
    "rpm",
    "cht",
    "egt",
    "oil_pressure",
    "oil_temp",
    "fuel_flow",
    "vibration",
    "battery_voltage",
    "alternator_health",
    "injection_timing",
    "throttle",
    "engine_load",
    "altitude",
    "ambient_temp",
    "engine_efficiency",
]

CORE_RESIDUAL_FIELDS: List[str] = [
    "rpm",
    "cht",
    "egt",
    "oil_pressure",
    "oil_temp",
    "fuel_flow",
    "vibration",
    "battery_voltage",
]

FAULT_TYPES: List[str] = [
    "injector_degradation",
    "misfire",
    "lubrication_problem",
    "overheating",
    "excessive_vibration",
    "combustion_instability",
    "sensor_drift",
    "sensor_failure",
    "fuel_system_degradation",
    "alternator_problem",
]


@dataclass(frozen=True)
class RuntimeConfig:
    sample_period_sec: float = 1.0
    initial_rul_hours: float = 480.0
    failure_health_threshold: float = 20.0


@dataclass(frozen=True)
class ModeDefaults:
    throttle: float
    engine_load: float
    altitude: float
    ambient_temp: float


MODE_DEFAULTS: Dict[str, ModeDefaults] = {
    "idle": ModeDefaults(throttle=0.15, engine_load=0.20, altitude=200.0, ambient_temp=22.0),
    "takeoff": ModeDefaults(throttle=0.95, engine_load=0.92, altitude=200.0, ambient_temp=22.0),
    "climb": ModeDefaults(throttle=0.82, engine_load=0.80, altitude=2000.0, ambient_temp=15.0),
    "cruise": ModeDefaults(throttle=0.66, engine_load=0.58, altitude=3500.0, ambient_temp=8.0),
    "loiter": ModeDefaults(throttle=0.50, engine_load=0.42, altitude=4200.0, ambient_temp=5.0),
    "high_load": ModeDefaults(throttle=0.80, engine_load=0.95, altitude=1200.0, ambient_temp=26.0),
    "descent": ModeDefaults(throttle=0.32, engine_load=0.28, altitude=1500.0, ambient_temp=16.0),
    "shutdown": ModeDefaults(throttle=0.0, engine_load=0.0, altitude=200.0, ambient_temp=22.0),
}


MISSION_PRESETS = {
    "normal_endurance": {
        "description": "Balanced mission with climb, cruise, loiter and descent phases.",
        "segments": [
            {"name": "idle", "duration_ratio": 0.08, "throttle": 0.15, "engine_load": 0.2, "altitude": 150, "ambient_temp": 22},
            {"name": "takeoff", "duration_ratio": 0.08, "throttle": 0.95, "engine_load": 0.92, "altitude": 250, "ambient_temp": 22},
            {"name": "climb", "duration_ratio": 0.18, "throttle": 0.84, "engine_load": 0.78, "altitude": 2800, "ambient_temp": 14},
            {"name": "cruise", "duration_ratio": 0.32, "throttle": 0.66, "engine_load": 0.58, "altitude": 4200, "ambient_temp": 8},
            {"name": "loiter", "duration_ratio": 0.20, "throttle": 0.50, "engine_load": 0.42, "altitude": 4300, "ambient_temp": 7},
            {"name": "descent", "duration_ratio": 0.14, "throttle": 0.30, "engine_load": 0.28, "altitude": 1200, "ambient_temp": 16},
        ],
    },
    "long_endurance": {
        "description": "Long-endurance mission with prolonged loiter at medium power.",
        "segments": [
            {"name": "idle", "duration_ratio": 0.06, "throttle": 0.14, "engine_load": 0.2, "altitude": 180, "ambient_temp": 21},
            {"name": "takeoff", "duration_ratio": 0.07, "throttle": 0.95, "engine_load": 0.92, "altitude": 260, "ambient_temp": 21},
            {"name": "climb", "duration_ratio": 0.17, "throttle": 0.82, "engine_load": 0.76, "altitude": 4300, "ambient_temp": 10},
            {"name": "loiter", "duration_ratio": 0.52, "throttle": 0.47, "engine_load": 0.40, "altitude": 4700, "ambient_temp": 6},
            {"name": "cruise", "duration_ratio": 0.10, "throttle": 0.62, "engine_load": 0.54, "altitude": 4200, "ambient_temp": 8},
            {"name": "descent", "duration_ratio": 0.08, "throttle": 0.30, "engine_load": 0.28, "altitude": 1100, "ambient_temp": 15},
        ],
    },
    "high_altitude": {
        "description": "Extended high-altitude operation with reduced air density effects.",
        "segments": [
            {"name": "takeoff", "duration_ratio": 0.08, "throttle": 0.96, "engine_load": 0.90, "altitude": 250, "ambient_temp": 20},
            {"name": "climb", "duration_ratio": 0.25, "throttle": 0.88, "engine_load": 0.80, "altitude": 6000, "ambient_temp": 0},
            {"name": "cruise", "duration_ratio": 0.45, "throttle": 0.72, "engine_load": 0.62, "altitude": 7600, "ambient_temp": -8},
            {"name": "descent", "duration_ratio": 0.22, "throttle": 0.36, "engine_load": 0.33, "altitude": 1300, "ambient_temp": 12},
        ],
    },
    "hot_weather": {
        "description": "High ambient-temperature mission stressing thermal behavior.",
        "segments": [
            {"name": "idle", "duration_ratio": 0.08, "throttle": 0.18, "engine_load": 0.25, "altitude": 200, "ambient_temp": 36},
            {"name": "takeoff", "duration_ratio": 0.10, "throttle": 0.95, "engine_load": 0.94, "altitude": 200, "ambient_temp": 38},
            {"name": "climb", "duration_ratio": 0.20, "throttle": 0.84, "engine_load": 0.80, "altitude": 2600, "ambient_temp": 28},
            {"name": "cruise", "duration_ratio": 0.40, "throttle": 0.70, "engine_load": 0.62, "altitude": 3500, "ambient_temp": 24},
            {"name": "descent", "duration_ratio": 0.22, "throttle": 0.32, "engine_load": 0.30, "altitude": 800, "ambient_temp": 30},
        ],
    },
    "high_load": {
        "description": "Mission biased toward sustained high load and thermal stress.",
        "segments": [
            {"name": "takeoff", "duration_ratio": 0.10, "throttle": 0.96, "engine_load": 0.95, "altitude": 250, "ambient_temp": 24},
            {"name": "high_load", "duration_ratio": 0.60, "throttle": 0.84, "engine_load": 0.95, "altitude": 2600, "ambient_temp": 18},
            {"name": "cruise", "duration_ratio": 0.20, "throttle": 0.72, "engine_load": 0.70, "altitude": 3200, "ambient_temp": 14},
            {"name": "descent", "duration_ratio": 0.10, "throttle": 0.30, "engine_load": 0.28, "altitude": 900, "ambient_temp": 18},
        ],
    },
    "rapid_throttle_transition": {
        "description": "Repeated fast throttle transitions to stress control response.",
        "segments": [
            {"name": "idle", "duration_ratio": 0.10, "throttle": 0.15, "engine_load": 0.2, "altitude": 300, "ambient_temp": 20},
            {"name": "takeoff", "duration_ratio": 0.10, "throttle": 0.95, "engine_load": 0.9, "altitude": 300, "ambient_temp": 20},
            {"name": "cruise", "duration_ratio": 0.10, "throttle": 0.45, "engine_load": 0.4, "altitude": 2000, "ambient_temp": 16},
            {"name": "high_load", "duration_ratio": 0.10, "throttle": 0.88, "engine_load": 0.92, "altitude": 2200, "ambient_temp": 16},
            {"name": "cruise", "duration_ratio": 0.10, "throttle": 0.48, "engine_load": 0.45, "altitude": 2000, "ambient_temp": 15},
            {"name": "high_load", "duration_ratio": 0.10, "throttle": 0.90, "engine_load": 0.94, "altitude": 2300, "ambient_temp": 15},
            {"name": "loiter", "duration_ratio": 0.20, "throttle": 0.50, "engine_load": 0.42, "altitude": 2800, "ambient_temp": 12},
            {"name": "descent", "duration_ratio": 0.20, "throttle": 0.30, "engine_load": 0.28, "altitude": 900, "ambient_temp": 17},
        ],
    },
}
