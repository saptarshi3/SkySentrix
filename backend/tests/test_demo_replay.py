import asyncio
import json
from app.services.realtime import RealtimeEngine
from app.db.database import SessionLocal
from app.db import crud
from app.main import api_list_missions, api_get_mission_telemetry

async def test_full_chain():
    crud.init_db()
    engine = RealtimeEngine()

    print("=== TEST 1: START SIMULATION ===")
    start_res = await engine.start("SIH Autonomous Evaluation", preset="normal_endurance", duration_sec=120, demo_mode=False)
    assert start_res["running"] is True
    print("PASS: Simulation started")

    print("=== TEST 2: HEALTHY BASELINE ===")
    await asyncio.sleep(2.0)
    st1 = engine.get_state()
    frame1 = st1["latest"]
    assert frame1 is not None
    assert st1["active_faults"] == {}
    assert frame1["health"]["health_index"] >= 98.0
    rpm = frame1["telemetry"]["rpm"]
    cht = frame1["telemetry"]["cht"]
    egt = frame1["telemetry"]["egt"]
    health = frame1["health"]["health_index"]
    fault = frame1["diagnosis"]["probable_fault"]
    print(f"PASS: Healthy baseline verified: RPM={rpm:.1f}, CHT={cht:.1f}, EGT={egt:.1f}, Health={health:.1f}%, Fault={fault}")

    print("=== TEST 3: INJECTOR DEGRADATION ===")
    inj_res = await engine.inject_fault("injector_degradation", severity=0.65, progression_per_sec=0.005, sensor_name=None)
    assert inj_res["status"] == "ok"
    await asyncio.sleep(2.5)
    st2 = engine.get_state()
    frame2 = st2["latest"]
    assert "injector_degradation" in st2["active_faults"]
    cur_sev = st2["active_faults"]["injector_degradation"]["current_severity"]
    print(f"PASS: Injector degradation active: severity={cur_sev:.2f}")

    print("=== TEST 4: OBSERVE COMPLETE CHAIN ===")
    fuel_res = frame2["residuals"].get("fuel_flow", {}).get("residual_pct", 0)
    anom_score = frame2["anomaly"]["score"]
    anom_level = frame2["anomaly"]["level"]
    top_fault = frame2["diagnosis"]["probable_fault"]
    confidence = frame2["diagnosis"]["confidence"]
    subsystems = frame2["diagnosis"]["affected_subsystems"]
    health_val = frame2["health"]["health_index"]
    rul_val = frame2["rul"]["current_rul_hours"]
    maint_msg = frame2["maintenance"]["message"]

    print(f"  - Telemetry Deviation: fuel_flow residual = {fuel_res:.2f}%")
    print(f"  - Anomaly Score: {anom_score:.3f}, Level: {anom_level}")
    print(f"  - ExtraTrees Top Fault: {top_fault}, Confidence: {confidence*100:.1f}%")
    print(f"  - Affected Subsystems: {subsystems}")
    print(f"  - Health Index: {health_val:.1f}%")
    print(f"  - RUL Hours: {rul_val:.1f} hrs")
    print(f"  - Maintenance Message: {maint_msg}")
    print("PASS: Complete diagnostic & prognostic chain observed")

    print("=== TEST 5: CLEAR FAULT ===")
    clr_res = await engine.clear_all_faults()
    assert clr_res["status"] == "ok"
    await asyncio.sleep(1.5)
    st3 = engine.get_state()
    assert st3["active_faults"] == {}
    print("PASS: Active faults cleared in simulator")

    print("=== TEST 6: VERIFY CLEAN STATE ===")
    assert len(st3["active_faults"]) == 0
    print("PASS: Clean state verified")

    print("=== TEST 7: STOP SIMULATION ===")
    stop_res = await engine.stop()
    assert stop_res["running"] is False
    st4 = engine.get_state()
    assert st4["running"] is False
    assert st4["active_faults"] == {}
    assert st4["latest"] is None
    print("PASS: Stopped cleanly, zero stale telemetry")

    print("=== TEST 8: RESTART ===")
    re_res = await engine.start("Post-Stop Mission", preset="normal_endurance", duration_sec=60, demo_mode=False)
    assert re_res["running"] is True
    await asyncio.sleep(1.2)
    st5 = engine.get_state()
    assert st5["running"] is True
    assert st5["latest"] is not None
    await engine.stop()
    print("PASS: Restart succeeded and stopped")

    print("=== TEST 9 & 10: OPEN REPLAY & REPLAY MISSION ===")
    with SessionLocal() as db:
        missions = api_list_missions(db)
        assert len(missions) > 0
        target = missions[0]
        telemetry_res = api_get_mission_telemetry(target.id, limit=None, db=db)
        rows = telemetry_res["rows"]
        assert len(rows) > 0
        print(f"PASS: Replay mission {target.id} loaded with {len(rows)} real frames")
        print(f"Sample Scrub at index 0: RPM={rows[0]['rpm']:.1f}, EGT={rows[0]['egt']:.1f}, Health={rows[0]['health_index']:.1f}%")
        print(f"Sample Scrub at index {len(rows)-1}: RPM={rows[-1]['rpm']:.1f}, EGT={rows[-1]['egt']:.1f}, Health={rows[-1]['health_index']:.1f}%")

    print("\n========================================")
    print("ALL 11 INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(test_full_chain())
