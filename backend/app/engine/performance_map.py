from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PerformanceSample:
    egt_c: float
    fuel_flow_lph: float
    efficiency: float
    vibration: float
    torque_nm: float


class PerformanceMap:
    """Synthetic parametric map with bilinear interpolation (prototype)."""

    def __init__(self) -> None:
        self.rpm_grid = np.array([800, 1200, 1600, 2000, 2400, 2800, 3200], dtype=float)
        self.load_grid = np.array([0.00, 0.25, 0.50, 0.75, 1.00], dtype=float)

        # Rows: rpm grid, Cols: load grid
        self.egt_map = np.array(
            [
                [500, 520, 545, 565, 585],
                [515, 540, 570, 600, 625],
                [530, 560, 595, 630, 660],
                [545, 585, 625, 670, 710],
                [560, 605, 650, 700, 750],
                [575, 620, 670, 725, 785],
                [585, 635, 690, 750, 810],
            ],
            dtype=float,
        )

        self.fuel_map = np.array(
            [
                [5.0, 7.5, 10.0, 12.5, 15.5],
                [7.0, 10.5, 14.0, 18.0, 22.0],
                [8.5, 13.0, 18.0, 23.0, 28.0],
                [10.0, 16.0, 22.0, 29.0, 36.0],
                [11.5, 18.5, 26.0, 34.0, 43.0],
                [13.0, 21.0, 30.0, 40.0, 51.0],
                [14.5, 23.5, 34.0, 45.0, 58.0],
            ],
            dtype=float,
        )

        self.eff_map = np.array(
            [
                [0.76, 0.80, 0.83, 0.84, 0.83],
                [0.79, 0.84, 0.87, 0.88, 0.87],
                [0.82, 0.87, 0.90, 0.91, 0.90],
                [0.84, 0.89, 0.92, 0.93, 0.92],
                [0.85, 0.90, 0.93, 0.94, 0.93],
                [0.84, 0.89, 0.92, 0.93, 0.92],
                [0.82, 0.87, 0.90, 0.91, 0.90],
            ],
            dtype=float,
        )

        self.vibration_map = np.array(
            [
                [0.16, 0.18, 0.20, 0.22, 0.24],
                [0.18, 0.20, 0.23, 0.26, 0.30],
                [0.20, 0.23, 0.27, 0.31, 0.36],
                [0.22, 0.26, 0.31, 0.36, 0.42],
                [0.25, 0.30, 0.36, 0.42, 0.49],
                [0.28, 0.34, 0.41, 0.48, 0.56],
                [0.32, 0.39, 0.47, 0.56, 0.65],
            ],
            dtype=float,
        )

        self.torque_map = np.array(
            [
                [40, 65, 95, 120, 145],
                [60, 95, 130, 165, 195],
                [75, 115, 160, 200, 235],
                [85, 130, 180, 225, 265],
                [92, 142, 195, 245, 285],
                [90, 138, 188, 235, 270],
                [82, 125, 170, 212, 245],
            ],
            dtype=float,
        )

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def _interp2(self, table: np.ndarray, rpm: float, load: float) -> float:
        rpm = self._clamp(rpm, float(self.rpm_grid[0]), float(self.rpm_grid[-1]))
        load = self._clamp(load, float(self.load_grid[0]), float(self.load_grid[-1]))

        i = int(np.searchsorted(self.rpm_grid, rpm) - 1)
        j = int(np.searchsorted(self.load_grid, load) - 1)
        i = max(0, min(i, len(self.rpm_grid) - 2))
        j = max(0, min(j, len(self.load_grid) - 2))

        r0, r1 = self.rpm_grid[i], self.rpm_grid[i + 1]
        l0, l1 = self.load_grid[j], self.load_grid[j + 1]

        q11 = table[i, j]
        q21 = table[i + 1, j]
        q12 = table[i, j + 1]
        q22 = table[i + 1, j + 1]

        tr = 0.0 if abs(r1 - r0) < 1e-9 else (rpm - r0) / (r1 - r0)
        tl = 0.0 if abs(l1 - l0) < 1e-9 else (load - l0) / (l1 - l0)

        return float(
            (1 - tr) * (1 - tl) * q11
            + tr * (1 - tl) * q21
            + (1 - tr) * tl * q12
            + tr * tl * q22
        )

    def sample(self, rpm: float, load: float, density_ratio: float) -> PerformanceSample:
        dr = self._clamp(density_ratio, 0.45, 1.2)

        egt = self._interp2(self.egt_map, rpm, load) + 22.0 * (1.0 - dr)
        fuel = self._interp2(self.fuel_map, rpm, load) * (1.0 + 0.10 * (1.0 - dr))
        eff = self._interp2(self.eff_map, rpm, load) * (0.95 + 0.05 * dr)
        vib = self._interp2(self.vibration_map, rpm, load)
        tq = self._interp2(self.torque_map, rpm, load) * dr

        return PerformanceSample(
            egt_c=egt,
            fuel_flow_lph=fuel,
            efficiency=self._clamp(eff, 0.65, 0.98),
            vibration=self._clamp(vib, 0.0, 5.0),
            torque_nm=max(0.0, tq),
        )
