import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.pipeline import DigitalTwinPipeline
from scripts.trajectory_utils import FAULT_TYPES, run_fault_trajectory

def dump_scores():
    for i, fault_type in enumerate(FAULT_TYPES):
        seed = 1000 + i
        pipeline = DigitalTwinPipeline()
        frames, sim = run_fault_trajectory(
            pipeline,
            preset="normal_endurance",
            seed=seed,
            duration_sec=180,
            fault_type=fault_type,
            severity=0.75,
            progression_per_sec=0.01,
            inject_at_step=60,
        )
        final_frame = frames[-1]
        print(f"\n{'='*40}")
        print(f"Fault: {fault_type}")
        print(f"Predicted: {final_frame.diagnosis.probable_fault}")
        print("Evidence:")
        for k, v in final_frame.diagnosis.evidence.items():
            print(f"  {k}: {v:.2f}")
        
        # To get the raw scores, we need to bypass the Pipeline wrapper and call the engine directly
        # But wait, we can just print the scores dict if we modify the engine to save it.
        # Alternatively, we can calculate them here manually.
        # But actually, the scores aren't saved in the frame. Let's just print the evidence for now.

if __name__ == "__main__":
    dump_scores()
