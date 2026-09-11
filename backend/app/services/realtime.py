from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

from app.config import RuntimeConfig
from app.db.database import SessionLocal
from app.engine.simulator import EngineSimulator
from app.models.schemas import ManualControlUpdateRequest
from app.services.pipeline import DigitalTwinPipeline


logger = logging.getLogger(__name__)


class TelemetryConnectionManager:
    def __init__(self) -> None:
        self.connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.connections:
                self.connections.remove(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self.connections)

        stale: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    if ws in self.connections:
                        self.connections.remove(ws)
 

class RealtimeEngine:
    def __init__(self) -> None:
        self.config = RuntimeConfig()
        self.simulator = EngineSimulator()
        self.pipeline = DigitalTwinPipeline()
        self.connection_manager = TelemetryConnectionManager()

        self.running = False
        self.loop_task: Optional[asyncio.Task] = None
        self.latest_payload: Optional[Dict[str, Any]] = None

        self.demo_mode = False
        self.demo_fault_stage = 0
        self.started_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def _step_and_broadcast(self, dt: Optional[float] = None) -> Optional[Dict[str, Any]]:
        async with self._lock:
            dt_val = dt if dt is not None else self.config.sample_period_sec
            point = self.simulator.step(dt_val)

            with SessionLocal() as db:
                frame = self.pipeline.process(db, point)

            payload = frame.model_dump(mode="json")
            payload["active_faults"] = self.simulator.get_faults()
            payload["sim_time_sec"] = self.simulator.time_sec
            payload["mission_elapsed_sec"] = self.simulator.mission_elapsed_sec
            payload["mission_duration_sec"] = self.simulator.mission_duration_sec

            self.latest_payload = payload
            await self.connection_manager.broadcast(payload)
            return payload

    async def start(self, mission_name: str, preset: str, duration_sec: int, demo_mode: bool) -> Dict[str, Any]:
        if self.running:
            await self.stop()

        logger.info("Starting simulation mission=%s preset=%s duration=%s demo_mode=%s", mission_name, preset, duration_sec, demo_mode)
        self.simulator.reset()
        self.simulator.load_mission(preset=preset, duration_sec=duration_sec, mission_name=mission_name)
        self.simulator.clear_all_faults()
        self.demo_mode = demo_mode
        self.demo_fault_stage = 0
        self.started_at = datetime.utcnow()

        with SessionLocal() as db:
            mission_id = self.pipeline.start_mission(
                db,
                name=mission_name,
                source="simulation",
                preset=preset,
                metadata={
                    "duration_sec": duration_sec,
                    "demo_mode": demo_mode,
                },
            )

        self.running = True
        self.loop_task = asyncio.create_task(self._run_loop(duration_sec))
        await self.connection_manager.broadcast({"type": "state", **self.get_state()})
        return {
            "running": True,
            "mission_id": mission_id,
            "mission_name": mission_name,
            "preset": preset,
            "demo_mode": demo_mode,
        }

    async def stop(self) -> Dict[str, Any]:
        logger.info("Stopping simulation")
        self.running = False

        if self.loop_task is not None and not self.loop_task.done():
            self.loop_task.cancel()
            try:
                await self.loop_task
            except asyncio.CancelledError:
                pass

        with SessionLocal() as db:
            self.pipeline.end_mission(db)
            self.pipeline.reset_state()

        self.simulator.clear_all_faults()
        self.latest_payload = None
        state = self.get_state()
        await self.connection_manager.broadcast({"type": "state", **state})

        return {"running": False}

    async def _run_loop(self, duration_sec: int) -> None:
        try:
            while self.running:
                self._advance_demo_script()
                await self._step_and_broadcast()

                if self.simulator.mission_elapsed_sec >= duration_sec:
                    self.running = False
                    break

                await asyncio.sleep(self.config.sample_period_sec)
        except asyncio.CancelledError:
            logger.info("Realtime simulation loop cancelled")
        finally:
            with SessionLocal() as db:
                self.pipeline.end_mission(db)
                self.pipeline.reset_state()
            self.running = False
            self.simulator.clear_all_faults()
            self.latest_payload = None
            state = self.get_state()
            await self.connection_manager.broadcast({"type": "state", **state})
            logger.info("Realtime simulation loop ended")

    def _advance_demo_script(self) -> None:
        if not self.demo_mode:
            return
        t = self.simulator.mission_elapsed_sec

        # One-click SIH demonstration progression
        if self.demo_fault_stage == 0 and t >= 45:
            self.simulator.inject_fault("injector_degradation", severity=0.35, progression_per_sec=0.004)
            self.demo_fault_stage = 1
        elif self.demo_fault_stage == 1 and t >= 120:
            self.simulator.inject_fault("injector_degradation", severity=0.72, progression_per_sec=0.005)
            self.demo_fault_stage = 2

    async def inject_fault(self, fault_type: str, severity: float, progression_per_sec: float, sensor_name: Optional[str]) -> Dict[str, Any]:
        self.simulator.inject_fault(fault_type, severity, progression_per_sec, sensor_name)
        if self.running:
            await self._step_and_broadcast()
        return {
            "status": "ok",
            "fault_type": fault_type,
            "severity": severity,
            "progression_per_sec": progression_per_sec,
            "sensor_name": sensor_name,
        }

    async def clear_fault(self, fault_type: str) -> Dict[str, Any]:
        self.simulator.clear_fault(fault_type)
        if not self.simulator.fault_manager.active_faults:
            self.pipeline.diagnosis.prediction_history.clear()
            self.pipeline.diagnosis.probability_history.clear()
        if self.running:
            await self._step_and_broadcast()
        else:
            self.pipeline.reset_state()
            self.latest_payload = None
            state = self.get_state()
            await self.connection_manager.broadcast({"type": "state", **state})
        return {"status": "ok", "fault_type": fault_type}

    async def clear_all_faults(self) -> Dict[str, Any]:
        self.simulator.clear_all_faults()
        self.pipeline.diagnosis.prediction_history.clear()
        self.pipeline.diagnosis.probability_history.clear()
        if self.running:
            await self._step_and_broadcast()
        else:
            self.pipeline.reset_state()
            self.latest_payload = None
            state = self.get_state()
            await self.connection_manager.broadcast({"type": "state", **state})
        return {"status": "ok"}

    def update_manual_controls(self, req: ManualControlUpdateRequest) -> Dict[str, Any]:
        self.simulator.set_manual_controls(
            mode=req.mode,
            throttle=req.throttle,
            engine_load=req.engine_load,
            altitude=req.altitude,
            ambient_temp=req.ambient_temp,
        )
        return {
            "status": "ok",
            "mode": self.simulator.mode,
            "throttle": self.simulator.throttle,
            "engine_load": self.simulator.engine_load_cmd,
            "altitude": self.simulator.altitude,
            "ambient_temp": self.simulator.ambient_temp,
        }

    def get_state(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "mode": self.simulator.mode,
            "throttle": self.simulator.throttle,
            "engine_load": self.simulator.engine_load_cmd,
            "altitude": self.simulator.altitude,
            "ambient_temp": self.simulator.ambient_temp,
            "active_faults": self.simulator.get_faults(),
            "demo_mode": self.demo_mode,
            "mission_elapsed_sec": self.simulator.mission_elapsed_sec,
            "mission_duration_sec": self.simulator.mission_duration_sec,
            "latest": self.latest_payload,
        }
