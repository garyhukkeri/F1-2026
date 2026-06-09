"""Monaco GP — did the penalised drivers actually exceed the 60 km/h pit-lane limit?

Method:
  The pit-lane controlled zone is the *limiter plateau*: the long, flat run where the
  car holds a near-constant low speed (throttle rising but speed pinned). Monaco's slow
  corners (Loews hairpin ~50-75, chicane) are short and are filtered out by requiring the
  LONGEST flat run. We report the held limiter level (median) and the in-zone peak, and
  compare against the 60 km/h limit. Telemetry x/y are unusable ('None'), so we use
  speed + per-lap distance only. Speed is GPS-derived and integer-rounded (~±1 km/h).
"""
import json
import pandas as pd
import numpy as np

BASE = "Monaco Grand Prix/Race"
LIMIT = 60.0

PENALIZED = ["HAM", "RUS", "COL", "GAS", "PIA"]

def is_set(v):
    return v not in (None, "None", "", "nan") and pd.notna(v)

def derive_passages(drv):
    with open(f"{BASE}/{drv}/laptimes.json") as f:
        lt = pd.DataFrame(json.load(f))
    ins = lt[lt["pin"].apply(is_set)]["lap"].astype(int).tolist()
    outs = lt[lt["pout"].apply(is_set)]["lap"].astype(int).tolist()
    return {"in": ins, "out": outs}

PASSAGES = {d: derive_passages(d) for d in PENALIZED}

def load_tel(drv, lap):
    with open(f"{BASE}/{drv}/{lap}_tel.json") as f:
        return pd.DataFrame(json.load(f)["tel"])

def limiter_plateau(drv, lap):
    """Longest flat low-speed run = pit-lane limiter zone."""
    t = load_tel(drv, lap).reset_index(drop=True)
    spd = t["speed"].astype(float).values
    dist = t["distance"].astype(float).values
    n = len(spd)
    # candidate samples: limiter band, exclude racing/approach (>72) and box crawl (<35)
    cand = (spd >= 35) & (spd <= 72)
    # flat = small step from previous sample (limiter holds speed)
    best = (0, -1, -1)
    i = 0
    while i < n:
        if cand[i]:
            j = i + 1
            while j < n and cand[j] and abs(spd[j] - spd[j-1]) <= 3:
                j += 1
            if (j - i) > best[0]:
                best = (j - i, i, j - 1)
            i = j
        else:
            i += 1
    ln, s, e = best
    if ln < 4:
        return None
    seg = spd[s:e+1]
    return {
        "lap": lap,
        "samples": int(ln),
        "held": float(np.median(seg)),
        "peak": float(seg.max()),
        "over_by": float(seg.max() - LIMIT),
        "n_over": int((seg > LIMIT).sum()),
        "frac_over": round(float((seg > LIMIT).mean()), 2),
        "dist0": float(dist[s]), "dist1": float(dist[e]),
        "trace": [float(x) for x in seg],
    }

rows = []
print(f"{'drv':>4} {'lap':>4} {'type':>4} {'phase':>12} {'held':>6} {'peak':>6} {'over+':>6} {'n>60':>5} {'%>60':>5}  verdict")
print("-" * 92)
for drv, p in PASSAGES.items():
    for kind, laps in (("IN", p["in"]), ("OUT", p["out"])):
        for lap in laps:
            try:
                r = limiter_plateau(drv, lap)
            except FileNotFoundError:
                continue
            if not r:
                continue
            r["drv"] = drv; r["type"] = kind
            r["phase"] = "green" if lap < 59 else "SC/red-flag"
            if r["held"] > LIMIT:
                v = "SUSTAINED OVER"
            elif r["peak"] > LIMIT and r["n_over"] >= 3:
                v = "brief breaches"
            elif r["peak"] > LIMIT:
                v = "rounding blip"
            else:
                v = "at/under limit"
            rows.append(r)
            r["verdict"] = v
            print(f"{drv:>4} {lap:>4} {kind:>4} {r['phase']:>12} {r['held']:>6.0f} {r['peak']:>6.0f} "
                  f"{r['over_by']:>+6.0f} {r['n_over']:>5} {int(r['frac_over']*100):>4}%  {v}")

# Save JSON for dashboard
out = {"limit": LIMIT, "passages": [{k: r[k] for k in
        ["drv","lap","type","phase","held","peak","over_by","n_over","frac_over","samples","dist0","dist1","trace","verdict"]}
        for r in rows]}
with open("analysis/monaco_pit_speed.json", "w") as f:
    json.dump(out, f)
print("\nwrote analysis/monaco_pit_speed.json with", len(rows), "passages")
