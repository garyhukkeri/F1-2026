import json
import pandas as pd

BASE = "Monaco Grand Prix/Race"

with open(f"{BASE}/rcm.json") as f:
    rcm = pd.DataFrame(json.load(f))

pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 200)

print("=== RCM columns ===")
print(rcm.columns.tolist())
print("Total messages:", len(rcm))

# Find penalty / pit / speed messages
mask = rcm["msg"].str.contains("PENALT|PIT|SPEED|KM/H|LIMIT|SECOND", case=False, na=False)
print("\n=== Penalty / pit / speed related messages ===")
for _, r in rcm[mask].iterrows():
    print(f"[{r['time']}] lap={r.get('lap')} cat={r.get('cat')} flag={r.get('flag')}")
    print(f"   {r['msg']}")

print("\n=== Safety Car / VSC / Red flag / Track status messages ===")
sc = rcm["msg"].str.contains("SAFETY CAR|VIRTUAL|SC |VSC|RED FLAG|RESTART|SUSPEND", case=False, na=False)
for _, r in rcm[sc].iterrows():
    print(f"[{r['time']}] lap={r.get('lap')} cat={r.get('cat')} | {r['msg']}")

# Pit stops & positions from session laptimes
with open(f"{BASE}/session_laptimes.json") as f:
    lt = pd.DataFrame(json.load(f))
print("\n=== Laptimes columns ===")
print(lt.columns.tolist())

with open(f"{BASE}/drivers.json") as f:
    drv = pd.json_normalize(json.load(f)["drivers"])

# Pit stops for penalized drivers
penalized = ["HAM", "RUS", "COL", "GAS", "PIA"]
print("\n=== Pit stops (laps with pin/pout) for penalized drivers ===")
for d in penalized:
    sub = lt[lt["drv"] == d]
    pins = sub[sub["pin"].notna()]["lap"].tolist()
    pouts = sub[sub["pout"].notna()]["lap"].tolist()
    print(f"{d}: pit-IN laps={pins}  pit-OUT laps={pouts}")

# Final classification = last recorded lap position per driver
print("\n=== Final classification (last lap pos) ===")
last = lt.sort_values("lap").groupby("drv").tail(1)[["drv", "lap", "pos"]]
last = last.sort_values("pos")
for _, r in last.iterrows():
    tag = " <-- penalized" if r["drv"] in penalized else ""
    print(f"P{int(r['pos']):>2}  {r['drv']}  (last lap {int(r['lap'])}){tag}")

# Total laps & how many cars pitted during SC laps 60-68
print("\n=== Pit activity by lap (SC window 60-68) ===")
pit_by_lap = lt[lt["pin"].notna()].groupby("lap")["drv"].apply(list)
for lap, drivers in pit_by_lap.items():
    flag = "  <-- SC/red-flag window" if 60 <= lap <= 68 else ""
    print(f"lap {int(lap):>2}: {len(drivers)} stops {drivers}{flag}")

