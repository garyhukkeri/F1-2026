"""Monaco GP Race — Leclerc brake-degradation diagnostic.

The dataset has NO brake-temperature / brake-wear channel (the `brake` signal is
binary pedal on/off). We therefore infer degradation indirectly via per-lap
braking behaviour at the two heaviest stops (T1 Sainte Devote, T10 Nouvelle
Chicane): brake point, brake distance, brake duration, entry speed, min speed.

Also captures the retirement lap (L65) profile so the dashboard can show exactly
where/when the car stopped.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Users/garyhukkeri/CodeSpace/p-projects/f1")
RACE = ROOT / "Monaco Grand Prix" / "Race"
OUT = ROOT / "analysis" / "monaco_lec_brake_deg.json"

# Apex distances (m) from corners.json for the two big stops.
ZONES = {
    "T1": {"apex": 194.23, "search": (40, 200)},     # Sainte Devote
    "T10": {"apex": 2044.52, "search": (1850, 2080)},  # Nouvelle Chicane
}


def load_tel(lap: int) -> pd.DataFrame:
    with open(RACE / "LEC" / f"{lap}_tel.json") as f:
        raw = json.load(f)
    return pd.DataFrame(raw["tel"]).sort_values("time").reset_index(drop=True)


def load_laps() -> pd.DataFrame:
    with open(RACE / "session_laptimes.json") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)
    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    return df[df["drv"] == "LEC"].sort_values("lap").reset_index(drop=True)


def brake_segments(tel: pd.DataFrame) -> list[tuple[float, float]]:
    brake = tel["brake"].astype(int).to_numpy()
    dist = tel["distance"].to_numpy()
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


def zone_metrics(tel: pd.DataFrame, apex: float, search: tuple[float, float]) -> dict | None:
    """Find the brake segment whose END falls just before the apex."""
    segs = brake_segments(tel)
    lo, hi = search
    cands = [(s, e) for (s, e) in segs if lo <= e <= hi]
    if not cands:
        return None
    s, e = min(cands, key=lambda se: abs(se[1] - apex))
    zone = tel[(tel["distance"] >= s) & (tel["distance"] <= e)]
    if zone.empty:
        return None
    after = tel[(tel["distance"] >= s) & (tel["distance"] <= e + 40)]
    return {
        "brake_start": s,
        "brake_end": e,
        "brake_distance": float(e - s),
        "brake_time": float(zone["time"].iloc[-1] - zone["time"].iloc[0]),
        "entry_speed": float(zone["speed"].iloc[0]),
        "min_speed": float(after["speed"].min()),
    }


def main() -> None:
    laps = load_laps()
    # Map lap -> status & lap_time for green-flag classification.
    lap_status = {int(r["lap"]): r for _, r in laps.iterrows()}

    per_lap = []
    for lap in range(1, 66):
        path = RACE / "LEC" / f"{lap}_tel.json"
        if not path.exists():
            continue
        tel = load_tel(lap)
        lt = lap_status.get(lap, {})
        lap_time = lt.get("time")
        lap_time = float(lap_time) if lap_time == lap_time and lap_time is not None else None  # NaN-safe
        status = str(lt.get("status", ""))
        compound = lt.get("compound")
        life = lt.get("life")
        # Green if status is exactly "1" and lap_time present & reasonable.
        green = (status == "1") and (lap_time is not None) and (lap_time < 90)

        row = {
            "lap": lap,
            "lap_time": lap_time,
            "status": status,
            "compound": compound,
            "life": int(life) if life == life and life is not None else None,
            "green": bool(green),
        }
        for zname, z in ZONES.items():
            m = zone_metrics(tel, z["apex"], z["search"])
            if m:
                row[f"{zname}_brake_start"] = m["brake_start"]
                row[f"{zname}_brake_distance"] = m["brake_distance"]
                row[f"{zname}_brake_time"] = m["brake_time"]
                row[f"{zname}_entry_speed"] = m["entry_speed"]
                row[f"{zname}_min_speed"] = m["min_speed"]

        # Braking deceleration actually achieved while on the pedal (acc_x, negative=stronger).
        # This is the key channel for "brakes not working": a healthy car pulls ~-10 to -12 m/s²;
        # a failing brake achieves far less for the same pedal input.
        ax = pd.to_numeric(tel["acc_x"], errors="coerce") if "acc_x" in tel.columns else None
        spd = pd.to_numeric(tel["speed"], errors="coerce")
        brake_on = tel["brake"].astype(int) == 1
        if ax is not None:
            sel = brake_on & (spd > 20)
            axb = ax[sel].dropna()
            if len(axb):
                row["median_decel"] = float(axb.median())
                row["p10_decel"] = float(axb.quantile(0.10))  # robust "strong braking"
                row["n_brake_samples"] = int(sel.sum())
        per_lap.append(row)

    # Retirement lap 65 profile (speed/brake over time + distance)
    t65 = load_tel(65)
    n = len(t65)
    if n > 700:
        idx = np.linspace(0, n - 1, 700).astype(int)
        t65s = t65.iloc[idx]
    else:
        t65s = t65
    moving = t65[t65["speed"] > 3]
    stop_time = float(moving["time"].iloc[-1]) if len(moving) else None
    stop_dist = float(moving["distance"].iloc[-1]) if len(moving) else None

    retirement = {
        "lap": 65,
        "time": t65s["time"].tolist(),
        "speed": t65s["speed"].tolist(),
        "brake": t65s["brake"].astype(int).tolist(),
        "distance": t65s["distance"].tolist(),
        "stop_time": stop_time,
        "stop_distance": stop_dist,
        "total_duration": float(t65["time"].iloc[-1] - t65["time"].iloc[0]),
    }

    # High-resolution "final approach" window: from 12 s before the stop to 2 s after,
    # at full sample rate, including longitudinal acceleration (acc_x).
    def num(col):
        return pd.to_numeric(t65[col], errors="coerce") if col in t65.columns else None

    accx = num("acc_x")
    fa_mask = (t65["time"] >= (stop_time - 12)) & (t65["time"] <= (stop_time + 2))
    fa = t65[fa_mask]
    final_approach = {
        "time": fa["time"].tolist(),
        "speed": fa["speed"].tolist(),
        "brake": fa["brake"].astype(int).tolist(),
        "throttle": pd.to_numeric(fa["throttle"], errors="coerce").tolist(),
        "distance": fa["distance"].tolist(),
        "acc_x": (accx[fa_mask].tolist() if accx is not None else []),
        "stop_time": stop_time,
        "stop_distance": stop_dist,
        # Peak (most negative) longitudinal deceleration in the window.
        "peak_decel": (float(accx[fa_mask].min()) if accx is not None else None),
        # Was brake on continuously over the last 3 s before the stop?
    }
    # Brake-on share over the final 3 s before the stop.
    last3 = t65[(t65["time"] >= stop_time - 3) & (t65["time"] <= stop_time)]
    final_approach["brake_on_pct_last3s"] = (
        float(last3["brake"].astype(int).mean() * 100) if len(last3) else None
    )
    final_approach["braking_at_stop"] = bool(
        len(last3) and int(last3["brake"].astype(int).iloc[-1]) == 1
    )

    payload = {
        "driver": "LEC",
        "name": "Charles Leclerc",
        "color": "#ED1131",
        "zones": list(ZONES.keys()),
        "per_lap": per_lap,
        "retirement": retirement,
        "final_approach": final_approach,
        "note": "No brake temperature/wear channel exists; degradation inferred from braking behaviour.",
    }
    with open(OUT, "w") as f:
        json.dump(payload, f)

    # ---- Console diagnostic ----
    df = pd.DataFrame(per_lap)
    green = df[df["green"]]
    print(f"Green-flag laps analysed: {len(green)} (laps {green['lap'].min()}-{green['lap'].max()})")
    for z in ZONES:
        sub = green.dropna(subset=[f"{z}_brake_start"])
        if sub.empty:
            continue
        early = sub[sub["lap"] <= sub["lap"].quantile(0.33)]
        late = sub[sub["lap"] >= sub["lap"].quantile(0.66)]
        print(f"\n== {z} ==")
        print(f"  brake_start  early={early[f'{z}_brake_start'].mean():.1f}m  late={late[f'{z}_brake_start'].mean():.1f}m  (lower = braking earlier)")
        print(f"  brake_dist   early={early[f'{z}_brake_distance'].mean():.1f}m  late={late[f'{z}_brake_distance'].mean():.1f}m")
        print(f"  brake_time   early={early[f'{z}_brake_time'].mean():.2f}s  late={late[f'{z}_brake_time'].mean():.2f}s")
        print(f"  entry_speed  early={early[f'{z}_entry_speed'].mean():.0f}    late={late[f'{z}_entry_speed'].mean():.0f}")
        print(f"  min_speed    early={early[f'{z}_min_speed'].mean():.0f}    late={late[f'{z}_min_speed'].mean():.0f}")
        # linear trend of brake_start vs lap
        x = sub["lap"].to_numpy(dtype=float)
        y = sub[f"{z}_brake_start"].to_numpy(dtype=float)
        if len(x) > 3:
            slope = np.polyfit(x, y, 1)[0]
            print(f"  brake_start trend: {slope:+.2f} m/lap (negative = brake point creeping earlier)")

    # Braking-strength collapse summary
    dd = df.dropna(subset=["median_decel"]) if "median_decel" in df.columns else pd.DataFrame()
    if not dd.empty:
        normal = dd[dd["lap"] <= 59]["median_decel"].median()
        failing = dd[dd["lap"] >= 60]["median_decel"].median()
        print(f"\nTypical braking deceleration (median, m/s^2): laps<=59 = {normal:.1f}, laps>=60 = {failing:.1f} "
              f"({(1-failing/normal)*100:.0f}% weaker)")

    print(f"\nRetirement (L65): car stopped at {stop_dist:.0f} m (~T19/main straight) "
          f"after {stop_time:.0f}s; lap logged for {retirement['total_duration']:.0f}s total.")
    print(f"  Brake at the moment of stopping: {final_approach['braking_at_stop']}")
    print(f"  Brake-on % over final 3 s: {final_approach['brake_on_pct_last3s']:.0f}%")
    print(f"  Peak longitudinal decel in final approach: {final_approach['peak_decel']:.1f} m/s^2 "
          f"(~{abs(final_approach['peak_decel'])/9.81:.2f} g)")
    print(f"Payload written: {OUT} ({OUT.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
