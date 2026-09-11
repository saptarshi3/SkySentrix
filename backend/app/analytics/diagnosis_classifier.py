from typing import Dict

def classify_fault(features: Dict[str, float]) -> Dict[str, float]:
    """Heuristic scoring for the five confused fault classes.
    Expected feature keys: egt_pos, fuel_flow_pos, fuel_flow_neg, vibration_pos,
    rpm_instability, rpm_abs, egt_instability, manifold_pos.
    Returns a dict mapping fault name to a score.
    """
    scores: Dict[str, float] = {}
    # Injector degradation: high egt excess and negative fuel flow excess (fuel reduction)
    scores['injector_degradation'] = 3.0 * features.get('egt_pos', 0.0) + 2.0 * features.get('fuel_flow_neg', 0.0)
    # Misfire: high rpm instability/abs and vibration
    scores['misfire'] = 2.5 * features.get('rpm_abs', 0.0) + 2.0 * features.get('rpm_instability', 0.0) + 1.5 * features.get('vibration_pos', 0.0)
    # Excessive vibration: dominant vibration, penalize rpm instability
    scores['excessive_vibration'] = 3.0 * features.get('vibration_pos', 0.0) - 0.5 * features.get('rpm_instability', 0.0)
    # Combustion instability: driven by egt instability
    scores['combustion_instability'] = 4.0 * features.get('egt_instability', 0.0) + 0.5 * features.get('vibration_pos', 0.0)
    # Fuel system degradation: positive fuel flow excess and manifold pressure
    scores['fuel_system_degradation'] = 2.5 * features.get('fuel_flow_pos', 0.0) + 1.5 * features.get('manifold_pos', 0.0)
    return scores
