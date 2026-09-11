"""
Shared helpers for generating simulator trajectories used by the Tier-1
calibration/testing scripts.

DATA PROVENANCE: every trajectory here comes from EngineSimulator (synthetic).
There is no real engine data involved anywhere in this module.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from app.engine.simulator import EngineSimulator
from app.models.schemas import PipelineFrame
from app.services.pipeline import DigitalTwinPipeline

PRESETS: List[str] = [
    "normal_endurance",
    "long_endurance",
    "high_altitude",
    "hot_weather",
    "high_load",
    "rapid_throttle_transition",
]

FAULT_TYPES: List[str] = [
    "injector_degradation",
    "misfire",
    "lubrication_problem",
    "overheating",
    "excessive_vibration",
    "combustion_instability",
    "fuel_system_degradation",
    "alternator_problem",
    "sensor_drift",
    "sensor_failure",
]


def run_healthy_trajectory(
    pipeline: DigitalTwinPipeline,
    preset: str,
    seed: int,
    duration_sec: int,
) -> List[PipelineFrame]:
    pipeline.reset_state()
    pipeline.current_preset = preset
    sim = EngineSimulator(seed=seed)
    sim.load_mission(preset, duration_sec=duration_sec, mission_name=f"ds-{preset}-{seed}")
    frames: List[PipelineFrame] = []
    for _ in range(duration_sec):
        point = sim.step(1.0)
        frame = pipeline.process(None, point)  # mission_id is None -> no DB writes
        frames.append(frame)
    return frames


def run_fault_trajectory(
    pipeline: DigitalTwinPipeline,
    preset: str,
    seed: int,
    duration_sec: int,
    fault_type: str,
    severity: float,
    progression_per_sec: float,
    inject_at_step: int,
) -> Tuple[List[PipelineFrame], EngineSimulator]:
    pipeline.reset_state()
    pipeline.current_preset = preset
    sim = EngineSimulator(seed=seed)
    sim.load_mission(preset, duration_sec=duration_sec, mission_name=f"ds-{preset}-{seed}-{fault_type}")
    frames: List[PipelineFrame] = []
    for step in range(duration_sec):
        if step == inject_at_step:
            sim.inject_fault(fault_type, severity=severity, progression_per_sec=progression_per_sec)
        point = sim.step(1.0)
        frame = pipeline.process(None, point)
        frames.append(frame)
    return frames, sim


def labels_for_fault_trajectory(duration_sec: int, inject_at_step: int, detect_delay_steps: int) -> List[bool]:
    """Ground-truth anomaly label per step: True from (inject + delay) onward.

    The delay is a documented assumption representing the time a fault needs
    to physically manifest in telemetry before it should be expected to be
    detectable — it is NOT tuned per fault to flatter any particular model.
    """
    return [step >= (inject_at_step + detect_delay_steps) for step in range(duration_sec)]
