"""Monaco GP Race — Ferrari braking analysis.

Builds the data payload (lap traces, per-corner metrics, race-long brake usage)
that the dashboard HTML consumes via injected JSON.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Users/garyhukkeri/CodeSpace/p-projects/f1")
RACE = ROOT / "Monaco Grand Prix" / "Race"
OUT = ROOT / "analysis" / "monaco_ferrari_brakes.json"

DRIVERS = ["LEC", "HAM"]
# Visual differentiation for two Ferrari drivers (same team color).
DRV_COLORS = {"LEC": "#ED1131", "HAM": "#FFD24D"}


def load_lap_telemetry(drv: str, lap: int) -> pd.DataFrame:
    path = RACE / drv / f"{lap}_tel.json"
    with open(path) as f:
        raw = json.load(f)
    df = pd.DataFrame(raw["tel"])
    # Some samples have distance=0 mid-lap; clean monotonic distance.
    df = df.sort_values("time").reset_index(drop=True)
    return df


def load_session_laptimes() -> pd.DataFrame:
    with open(RACE / "session_laptimes.json") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)
    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    return df


def load_corners() -> pd.DataFrame:
    with open(RACE / "corners.json") as f:
        raw = json.load(f)
    return pd.DataFrame(raw)


def best_clean_lap(df: pd.DataFrame, drv: str) -> int:
    sub = df[(df["drv"] == drv) & (df["del"] == False) & (df["iacc"] == True) & df["time"].notna()]
    return int(sub.nsmallest(1, "time")["lap"].iloc[0])


def brake_segments(tel: pd.DataFrame) -> list[tuple[float, float]]:
    """Return list of (start_distance, end_distance) for brake-on segments."""
    brake = tel["brake"].astype(int).to_numpy()
    dist = tel["distance"].to_numpy()
    segs: list[tuple[float, float]] = []
    in_seg = False
    s = 0.0
    for i, b in enumerate(brake):
        if b == 1 and not in_seg:
            in_seg = True
            s = float(dist[i])
        elif b == 0 and in_seg:
            in_seg = False
            segs.append((s, float(dist[i])))
    if in_seg:
        segs.append((s, float(dist[-1])))
    # Filter junk segments (length < 5 m) — sensor noise / launch.
    segs = [seg for seg in segs if seg[1] - seg[0] >= 5.0]
    return segs


def per_corner_metrics(tel: pd.DataFrame, corners: pd.DataFrame) -> list[dict]:
    """For each corner, locate the braking zone immediately preceding apex distance
    and compute entry speed, min speed, brake distance, brake time.
    """
    rows: list[dict] = []
    segs = brake_segments(tel)
    lap_len = float(tel["distance"].max())

    for _, c in corners.iterrows():
        apex = float(c["Distance"])
        # Find the brake segment that ends within ~120 m before / 50 m after the apex.
        candidates = [
            (s, e) for (s, e) in segs
            if (apex - 200) <= e <= (apex + 50)
        ]
        if not candidates:
            rows.append({
                "corner": int(c["CornerNumber"]),
                "apex": apex,
                "brake_start": None,
                "brake_end": None,
                "brake_distance": 0.0,
                "brake_time": 0.0,
                "entry_speed": None,
                "min_speed": None,
            })
            continue
        # Pick the one closest in end-distance to apex.
        seg = min(candidates, key=lambda se: abs(se[1] - apex))
        s, e = seg
        # Slice telemetry within [s, e].
        mask = (tel["distance"] >= s) & (tel["distance"] <= e)
        zone = tel[mask]
        if zone.empty:
            continue
        entry_speed = float(zone["speed"].iloc[0])
        # Min speed is min within zone AND a short window after (some corners min after release).
        after_mask = (tel["distance"] >= s) & (tel["distance"] <= e + 40)
        min_speed = float(tel.loc[after_mask, "speed"].min())
        brake_time = float(zone["time"].iloc[-1] - zone["time"].iloc[0])
        rows.append({
            "corner": int(c["CornerNumber"]),
            "apex": apex,
            "brake_start": s,
            "brake_end": e,
            "brake_distance": float(e - s),
            "brake_time": brake_time,
            "entry_speed": entry_speed,
            "min_speed": min_speed,
        })
    return rows


def brake_pct_per_lap(drv: str, laps_to_use: list[int]) -> list[dict]:
    """For each available race lap, compute fraction of lap time on brakes."""
    out: list[dict] = []
    drv_dir = RACE / drv
    for lap in laps_to_use:
        path = drv_dir / f"{lap}_tel.json"
        if not path.exists():
            continue
        try:
            with open(path) as f:
                raw = json.load(f)
            tel = pd.DataFrame(raw["tel"])
        except Exception:
            continue
        if tel.empty or "brake" not in tel.columns:
            continue
        tel = tel.sort_values("time").reset_index(drop=True)
        # Estimate sample time spent on brakes via dt between consecutive samples.
        dt = tel["time"].diff().fillna(0).clip(lower=0, upper=0.5)
        brake_time = float(dt[tel["brake"].astype(int) == 1].sum())
        total_time = float(dt.sum())
        if total_time <= 0:
            continue
        # Brake distance fraction
        dd = tel["distance"].diff().fillna(0).clip(lower=0)
        brake_dist = float(dd[tel["brake"].astype(int) == 1].sum())
        total_dist = float(dd.sum())
        # Count brake applications (rising edges)
        b = tel["brake"].astype(int).to_numpy()
        applications = int(((b[1:] == 1) & (b[:-1] == 0)).sum())
        out.append({
            "lap": int(lap),
            "brake_pct_time": (brake_time / total_time) * 100.0,
            "brake_pct_dist": (brake_dist / total_dist) * 100.0 if total_dist else 0.0,
            "brake_applications": applications,
            "lap_time": total_time,
        })
    return out


def downsample(values: list[float], target: int = 600) -> list[float]:
    if len(values) <= target:
        return values
    idx = np.linspace(0, len(values) - 1, target).astype(int)
    return [values[i] for i in idx]


def main() -> None:
    laps_df = load_session_laptimes()
    corners = load_corners().sort_values("Distance").reset_index(drop=True)

    lec_best = best_clean_lap(laps_df, "LEC")
    ham_best = best_clean_lap(laps_df, "HAM")

    lec_row = laps_df[(laps_df["drv"] == "LEC") & (laps_df["lap"] == lec_best)].iloc[0]
    ham_row = laps_df[(laps_df["drv"] == "HAM") & (laps_df["lap"] == ham_best)].iloc[0]

    lec_tel = load_lap_telemetry("LEC", lec_best)
    ham_tel = load_lap_telemetry("HAM", ham_best)

    # Per-corner metrics on the chosen laps
    lec_corners = per_corner_metrics(lec_tel, corners)
    ham_corners = per_corner_metrics(ham_tel, corners)

    # Race-long brake usage
    lec_race_laps = sorted({int(l) for l in laps_df[laps_df["drv"] == "LEC"]["lap"].tolist()})
    ham_race_laps = sorted({int(l) for l in laps_df[laps_df["drv"] == "HAM"]["lap"].tolist()})
    lec_brakes = brake_pct_per_lap("LEC", lec_race_laps)
    ham_brakes = brake_pct_per_lap("HAM", ham_race_laps)

    def tel_trace(tel: pd.DataFrame) -> dict:
        # downsample for browser
        n = len(tel)
        if n > 1200:
            idx = np.linspace(0, n - 1, 1200).astype(int)
            tel = tel.iloc[idx].reset_index(drop=True)
        return {
            "distance": tel["distance"].tolist(),
            "speed": tel["speed"].tolist(),
            "brake": tel["brake"].astype(int).tolist(),
            "throttle": tel["throttle"].tolist(),
            "x": tel["x"].tolist(),
            "y": tel["y"].tolist(),
        }

    payload = {
        "event": "Monaco Grand Prix",
        "session": "Race",
        "drivers": {
            "LEC": {
                "name": "Charles Leclerc",
                "color": DRV_COLORS["LEC"],
                "best_lap": lec_best,
                "best_lap_time": float(lec_row["time"]),
                "best_lap_compound": lec_row["compound"],
                "best_lap_life": int(lec_row["life"]),
                "trace": tel_trace(lec_tel),
                "corners": lec_corners,
                "race_brakes": lec_brakes,
            },
            "HAM": {
                "name": "Lewis Hamilton",
                "color": DRV_COLORS["HAM"],
                "best_lap": ham_best,
                "best_lap_time": float(ham_row["time"]),
                "best_lap_compound": ham_row["compound"],
                "best_lap_life": int(ham_row["life"]),
                "trace": tel_trace(ham_tel),
                "corners": ham_corners,
                "race_brakes": ham_brakes,
            },
        },
        "corners": corners.to_dict(orient="records"),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f)

    # Sanity print
    print(f"LEC fastest race lap: L{lec_best} {lec_row['time']:.3f}s ({lec_row['compound']}, life {int(lec_row['life'])})")
    print(f"HAM fastest race lap: L{ham_best} {ham_row['time']:.3f}s ({ham_row['compound']}, life {int(ham_row['life'])})")
    print(f"LEC brake-on % of lap (best lap): {sum(c['brake_time'] for c in lec_corners):.2f}s")
    print(f"HAM brake-on % of lap (best lap): {sum(c['brake_time'] for c in ham_corners):.2f}s")
    print(f"LEC race laps with telemetry: {len(lec_brakes)}")
    print(f"HAM race laps with telemetry: {len(ham_brakes)}")
    print(f"Payload written: {OUT} ({OUT.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
