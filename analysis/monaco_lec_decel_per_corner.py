"""Monaco GP Race — Leclerc deceleration per corner, per lap.

For each corner we locate the braking zone (brake-on segment ending just before
the apex) and compute the deceleration actually achieved there from the
longitudinal accelerometer (acc_x, negative = decelerating).

Output supports a line chart: x = corner (T1..T19), one line = average over the
healthy laps (1-59), plus one line for each of the final laps (60-65).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Users/garyhukkeri/CodeSpace/p-projects/f1")
RACE = ROOT / "Monaco Grand Prix" / "Race"
OUT = ROOT / "analysis" / "monaco_lec_decel_per_corner.json"

FINAL_LAPS = [60, 61, 62, 63, 64, 65]


def load_tel(lap: int) -> pd.DataFrame:
    with open(RACE / "LEC" / f"{lap}_tel.json") as f:
        raw = json.load(f)
    t = pd.DataFrame(raw["tel"]).sort_values("time").reset_index(drop=True)
    for c in ("speed", "distance", "acc_x"):
        if c in t.columns:
            t[c] = pd.to_numeric(t[c], errors="coerce")
    t["brake"] = t["brake"].astype(int)
    return t


def load_corners() -> pd.DataFrame:
    with open(RACE / "corners.json") as f:
        raw = json.load(f)
    return pd.DataFrame(raw).sort_values("Distance").reset_index(drop=True)


def brake_segments(t: pd.DataFrame) -> list[tuple[float, float]]:
    brake = t["brake"].to_numpy()
    dist = t["distance"].to_numpy()
    segs, in_seg, s = [], False, 0.0
    for i, b in enumerate(brake):
        if b == 1 and not in_seg:
            in_seg, s = True, float(dist[i])
        elif b == 0 and in_seg:
            in_seg = False
            segs.append((s, float(dist[i])))
    if in_seg:
        segs.append((s, float(dist[-1])))
    return [seg for seg in segs if seg[1] - seg[0] >= 5.0]


def corner_decel(t: pd.DataFrame, apex: float) -> float | None:
    """Mean deceleration (acc_x) over the brake-on samples in the zone ending
    just before this apex. Returns None if no braking detected there."""
    segs = brake_segments(t)
    cands = [(s, e) for (s, e) in segs if (apex - 200) <= e <= (apex + 50)]
    if not cands:
        return None
    s, e = min(cands, key=lambda se: abs(se[1] - apex))
    zone = t[(t["distance"] >= s) & (t["distance"] <= e) & (t["brake"] == 1)]
    ax = zone["acc_x"].dropna()
    # Drop clearly non-physical spikes (|a| > 25 m/s^2 ~ 2.5g) so a single impact
    # sample doesn't dominate the mean. The crash impact on L65/T19 is thus excluded.
    ax = ax[ax.abs() <= 25]
    if ax.empty:
        return None
    return float(ax.mean())


def main() -> None:
    corners = load_corners()
    apexes = {int(r["CornerNumber"]): float(r["Distance"]) for _, r in corners.iterrows()}
    corner_nums = sorted(apexes.keys())

    # per_lap_corner[lap][corner] = mean decel
    per_lap_corner: dict[int, dict[int, float]] = {}
    for lap in range(1, 66):
        path = RACE / "LEC" / f"{lap}_tel.json"
        if not path.exists():
            continue
        t = load_tel(lap)
        per_lap_corner[lap] = {}
        for cn in corner_nums:
            d = corner_decel(t, apexes[cn])
            if d is not None:
                per_lap_corner[lap][cn] = d

    # Baseline = mean over laps 1-59 (per corner, equal lap weighting).
    baseline = {}
    baseline_n = {}
    for cn in corner_nums:
        vals = [per_lap_corner[l][cn] for l in range(1, 60)
                if l in per_lap_corner and cn in per_lap_corner[l]]
        if vals:
            baseline[cn] = float(np.mean(vals))
            baseline_n[cn] = len(vals)

    final = {}
    for lap in FINAL_LAPS:
        if lap in per_lap_corner:
            final[lap] = {cn: per_lap_corner[lap].get(cn) for cn in corner_nums}

    # Average over the "failure" laps before the last one (60-64).
    failure_laps = [l for l in FINAL_LAPS if l != 65]
    failure_avg = {}
    for cn in corner_nums:
        vals = [per_lap_corner[l][cn] for l in failure_laps
                if l in per_lap_corner and cn in per_lap_corner[l]]
        if vals:
            failure_avg[cn] = float(np.mean(vals))

    last_lap = final.get(65, {})

    payload = {
        "driver": "LEC",
        "name": "Charles Leclerc",
        "corners": corner_nums,
        "metric": "mean deceleration while braking (acc_x, m/s^2, negative = stronger)",
        "baseline": {str(cn): baseline.get(cn) for cn in corner_nums},
        "baseline_label": "Avg laps 1-59",
        "failure_avg": {str(cn): failure_avg.get(cn) for cn in corner_nums},
        "failure_avg_label": "Avg laps 60-64",
        "last_lap": {str(cn): last_lap.get(cn) for cn in corner_nums},
        "last_lap_label": "Lap 65 (final)",
        "final_laps": {str(lap): {str(cn): final[lap].get(cn) for cn in corner_nums} for lap in final},
        "note": "Braking corners only; T2/T9 are flat (no braking). Impact spikes > 2.5g excluded.",
    }
    with open(OUT, "w") as f:
        json.dump(payload, f)

    # Console summary table
    print("Deceleration per corner (m/s^2, mean while braking; negative = stronger):\n")
    hdr = "Corner | " + "Base  | " + " | ".join(f"L{l}" for l in FINAL_LAPS)
    print(hdr)
    for cn in corner_nums:
        if cn not in baseline:
            continue
        cells = [f"{baseline[cn]:5.1f}"]
        for l in FINAL_LAPS:
            v = final.get(l, {}).get(cn)
            cells.append(f"{v:5.1f}" if v is not None else "  -- ")
        print(f"  T{cn:<3} | " + " | ".join(cells))
    print(f"\nPayload written: {OUT} ({OUT.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
