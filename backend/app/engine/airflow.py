from __future__ import annotations


class AirflowModel:
    """Reduced-order air mass flow model for 4-stroke piston engine."""

    def __init__(self) -> None:
        self.displacement_m3 = 0.0036  # 3.6L equivalent class (prototype assumption)

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def compute(
        self,
        *,
        rpm: float,
        manifold_pressure_kpa: float,
        ambient_pressure_kpa: float,
        density_kg_m3: float,
        throttle: float,
        combustion_health: float,
    ) -> float:
        pressure_ratio = self._clamp(manifold_pressure_kpa / max(ambient_pressure_kpa, 20.0), 0.25, 1.1)
        volumetric_eff = (0.62 + 0.28 * throttle + 0.14 * pressure_ratio) * self._clamp(combustion_health, 0.6, 1.0)
        volumetric_eff = self._clamp(volumetric_eff, 0.45, 1.10)

        # 4-stroke: one intake event every 2 crank revolutions.
        intake_volume_per_sec = self.displacement_m3 * max(rpm, 0.0) / 120.0
        m_dot_air = intake_volume_per_sec * density_kg_m3 * volumetric_eff

        return self._clamp(m_dot_air, 0.0, 2.0)
