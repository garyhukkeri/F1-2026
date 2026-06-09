#!/usr/bin/env python3
"""
Chinese GP Race: Hamilton vs Antonelli
Average speed comparison across each corner and straight.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE      = Path("/Users/garyhukkeri/CodeSpace/p-projects/f1")
RACE_DIR  = BASE / "Chinese Grand Prix" / "Race"
VIZ_DIR   = BASE / "visualizations"
CORNER_ZONE = 150   # metres either side of apex

DRIVER_COLORS = {
    "HAM": "#E8002D",   # Ferrari red
    "ANT": "#27F4D2",   # Mercedes teal
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_json(path):
    with open(path) as f:
        return json.load(f)

# ── Load corners ──────────────────────────────────────────────────────────────
print("Loading corner data...")
corners = pd.DataFrame(load_json(RACE_DIR / "corners.json")) \
            .sort_values("Distance").reset_index(drop=True)
print(f"  {len(corners)} corners  |  "
      f"distance range {corners['Distance'].min():.0f}m – {corners['Distance'].max():.0f}m")

# ── Estimate track length from a mid-race lap ─────────────────────────────────
sample_tel = pd.DataFrame(load_json(RACE_DIR / "HAM" / "10_tel.json")["tel"])
track_length = sample_tel["distance"].max() * 1.02
print(f"  Track length estimate: {track_length:.0f}m")

# ── Build segment map ─────────────────────────────────────────────────────────
def build_segments(corners_df, track_len, zone=CORNER_ZONE):
    segs = []
    n = len(corners_df)
    for i in range(n):
        row      = corners_df.iloc[i]
        apex     = row["Distance"]
        cnum     = int(row["CornerNumber"])
        c_start  = max(0.0, apex - zone)
        c_end    = min(track_len, apex + zone)

        # Straight before this corner
        if i == 0:
            prev_end  = 0.0
            prev_cnum = int(corners_df.iloc[-1]["CornerNumber"])
        else:
            prev_end  = corners_df.iloc[i-1]["Distance"] + zone
            prev_cnum = int(corners_df.iloc[i-1]["CornerNumber"])

        if c_start > prev_end + 10:
            segs.append(dict(type="straight", name=f"S{prev_cnum}→{cnum}",
                             start=prev_end, end=c_start))

        segs.append(dict(type="corner", name=f"T{cnum}",
                         start=c_start, end=c_end))

    # Start/finish straight (after last corner)
    last_end  = corners_df.iloc[-1]["Distance"] + zone
    first_c   = int(corners_df.iloc[0]["CornerNumber"])
    last_c    = int(corners_df.iloc[-1]["CornerNumber"])
    if last_end < track_len - 10:
        segs.append(dict(type="straight", name=f"S{last_c}→{first_c}",
                         start=last_end, end=track_len))
    return segs

segments = build_segments(corners, track_length)
print(f"\nSegment map ({len(segments)} segments):")
for s in segments:
    print(f"  [{s['type']:8s}] {s['name']:12s}  {s['start']:.0f}m – {s['end']:.0f}m")

# ── Vectorised classification ─────────────────────────────────────────────────
def classify(distances_arr, segs):
    labels = np.full(len(distances_arr), "other", dtype=object)
    for seg in segs:
        mask = (distances_arr >= seg["start"]) & (distances_arr < seg["end"])
        labels[mask] = seg["name"]
    return labels

# ── Load valid race laps ──────────────────────────────────────────────────────
def get_valid_laps(driver):
    raw = load_json(RACE_DIR / driver / "laptimes.json")
    df  = pd.DataFrame(raw)
    # Remove deleted laps
    df = df[df["del"] != True]
    # Keep only accurately-timed laps
    df = df[df["iacc"] == True]
    # Skip lap 1 (standing start chaos)
    df = df[df["lap"] > 1]
    # Skip pit-in laps (pin is not 'None')
    df = df[df["pin"] == "None"]
    # Skip pit-out laps (pout is not 'None')
    df = df[df["pout"] == "None"]
    return sorted(df["lap"].dropna().astype(int).tolist())

# ── Process a driver: load telemetry → classify → aggregate ──────────────────
def process_driver(driver):
    valid_laps = get_valid_laps(driver)
    print(f"\n{driver}: {len(valid_laps)} valid laps")

    all_data = []
    for lap in valid_laps:
        tel_path = RACE_DIR / driver / f"{lap}_tel.json"
        if not tel_path.exists():
            continue
        tel = pd.DataFrame(load_json(tel_path)["tel"])
        if "distance" not in tel.columns or "speed" not in tel.columns:
            continue

        tel["segment"] = classify(tel["distance"].values, segments)
        tel = tel[tel["segment"] != "other"]

        lap_agg = tel.groupby("segment")["speed"].mean().reset_index()
        lap_agg["lap"] = lap
        all_data.append(lap_agg)

    if not all_data:
        return pd.DataFrame(columns=["segment", "speed", "driver"])

    combined = pd.concat(all_data, ignore_index=True)
    result   = combined.groupby("segment")["speed"].mean().reset_index()
    result["driver"] = driver
    return result

ham_data = process_driver("HAM")
ant_data = process_driver("ANT")

# ── Prepare per-segment chart arrays ─────────────────────────────────────────
corner_segs   = [s["name"] for s in segments if s["type"] == "corner"]
straight_segs = [s["name"] for s in segments if s["type"] == "straight"]

def get_speeds(data, seg_names):
    d = dict(zip(data["segment"], data["speed"]))
    return [round(float(d.get(n, 0)), 1) for n in seg_names]

ham_c = get_speeds(ham_data, corner_segs)
ant_c = get_speeds(ant_data, corner_segs)
ham_s = get_speeds(ham_data, straight_segs)
ant_s = get_speeds(ant_data, straight_segs)

corner_delta   = [round(h - a, 1) for h, a in zip(ham_c, ant_c)]
straight_delta = [round(h - a, 1) for h, a in zip(ham_s, ant_s)]

print("\nCorner avg speeds (km/h):")
for seg, h, a in zip(corner_segs, ham_c, ant_c):
    print(f"  {seg:12s}  HAM={h:.1f}  ANT={a:.1f}  Δ={h-a:+.1f}")
print("\nStraight avg speeds (km/h):")
for seg, h, a in zip(straight_segs, ham_s, ant_s):
    print(f"  {seg:14s}  HAM={h:.1f}  ANT={a:.1f}  Δ={h-a:+.1f}")

# ── Build HTML section ────────────────────────────────────────────────────────
VIZ_DIR.mkdir(exist_ok=True)
out_path  = VIZ_DIR / "chinese-gp-race.html"
ts        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
sid       = datetime.now().strftime("%Y%m%d%H%M%S")
hc, ac    = DRIVER_COLORS["HAM"], DRIVER_COLORS["ANT"]

# Delta colours: red when HAM faster, teal when ANT faster
def delta_colors(deltas, pos_col, neg_col):
    return [pos_col if v >= 0 else neg_col for v in deltas]

c_delta_cols = delta_colors(corner_delta,   hc, ac)
s_delta_cols = delta_colors(straight_delta, hc, ac)
all_segs     = corner_segs + straight_segs
all_deltas   = corner_delta + straight_delta
all_d_cols   = delta_colors(all_deltas, hc, ac)

section = f"""
<div class="analysis-section" id="analysis-{sid}">
  <div class="section-title">Hamilton vs Antonelli — Average Speed by Segment</div>
  <div class="section-timestamp">Generated: {ts} · Chinese GP Race · All valid clean laps</div>

  <div class="chart-label">Corner Speeds (km/h)</div>
  <div id="chart-corners-{sid}" class="chart"></div>

  <div class="chart-label" style="margin-top:40px">Straight Speeds (km/h)</div>
  <div id="chart-straights-{sid}" class="chart"></div>

  <div class="chart-label" style="margin-top:40px">Speed Delta — Hamilton minus Antonelli (km/h) · Red = HAM faster · Teal = ANT faster</div>
  <div id="chart-delta-{sid}" class="chart" style="height:380px"></div>
</div>
<script>
(function() {{
  // ── Corners ──────────────────────────────────────────────────────────────
  var cChart = echarts.init(document.getElementById('chart-corners-{sid}'), 'dark');
  cChart.setOption({{
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }},
      formatter: function(p) {{
        return p[0].name + '<br>'
          + '<span style="color:{hc}">●</span> Hamilton: ' + p[0].value + ' km/h<br>'
          + '<span style="color:{ac}">●</span> Antonelli: ' + p[1].value + ' km/h';
      }}
    }},
    legend: {{ data: ['Hamilton', 'Antonelli'], top: 8 }},
    toolbox: {{ feature: {{ saveAsImage: {{}}, dataZoom: {{}} }} }},
    grid: {{ left: 65, right: 20, bottom: 70, top: 50 }},
    xAxis: {{ type: 'category', data: {json.dumps(corner_segs)},
              axisLabel: {{ rotate: 0, fontSize: 12 }} }},
    yAxis: {{ type: 'value', name: 'km/h',
              min: function(v) {{ return Math.floor(v.min * 0.97); }},
              nameTextStyle: {{ color: '#aaa' }} }},
    series: [
      {{ name: 'Hamilton',  type: 'bar', barGap: '5%',
         data: {json.dumps(ham_c)}, itemStyle: {{ color: '{hc}' }} }},
      {{ name: 'Antonelli', type: 'bar', barGap: '5%',
         data: {json.dumps(ant_c)}, itemStyle: {{ color: '{ac}' }} }}
    ]
  }});
  window.addEventListener('resize', () => cChart.resize());

  // ── Straights ─────────────────────────────────────────────────────────────
  var sChart = echarts.init(document.getElementById('chart-straights-{sid}'), 'dark');
  sChart.setOption({{
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }},
      formatter: function(p) {{
        return p[0].name + '<br>'
          + '<span style="color:{hc}">●</span> Hamilton: ' + p[0].value + ' km/h<br>'
          + '<span style="color:{ac}">●</span> Antonelli: ' + p[1].value + ' km/h';
      }}
    }},
    legend: {{ data: ['Hamilton', 'Antonelli'], top: 8 }},
    toolbox: {{ feature: {{ saveAsImage: {{}}, dataZoom: {{}} }} }},
    grid: {{ left: 65, right: 20, bottom: 100, top: 50 }},
    xAxis: {{ type: 'category', data: {json.dumps(straight_segs)},
              axisLabel: {{ rotate: 35, fontSize: 11 }} }},
    yAxis: {{ type: 'value', name: 'km/h',
              min: function(v) {{ return Math.floor(v.min * 0.97); }},
              nameTextStyle: {{ color: '#aaa' }} }},
    series: [
      {{ name: 'Hamilton',  type: 'bar', barGap: '5%',
         data: {json.dumps(ham_s)}, itemStyle: {{ color: '{hc}' }} }},
      {{ name: 'Antonelli', type: 'bar', barGap: '5%',
         data: {json.dumps(ant_s)}, itemStyle: {{ color: '{ac}' }} }}
    ]
  }});
  window.addEventListener('resize', () => sChart.resize());

  // ── Delta (all segments) ──────────────────────────────────────────────────
  var dChart = echarts.init(document.getElementById('chart-delta-{sid}'), 'dark');
  var allSegs   = {json.dumps(all_segs)};
  var allDeltas = {json.dumps(all_deltas)};
  var dColors   = {json.dumps(all_d_cols)};
  dChart.setOption({{
    tooltip: {{
      trigger: 'axis',
      formatter: function(p) {{
        var v = p[0].value;
        var who = v >= 0 ? 'Hamilton +' : 'Antonelli +';
        return p[0].name + '<br>' + who + Math.abs(v).toFixed(1) + ' km/h';
      }}
    }},
    toolbox: {{ feature: {{ saveAsImage: {{}} }} }},
    grid: {{ left: 65, right: 20, bottom: 100, top: 30 }},
    xAxis: {{ type: 'category', data: allSegs,
              axisLabel: {{ rotate: 35, fontSize: 11 }} }},
    yAxis: {{ type: 'value', name: 'Δ km/h', nameTextStyle: {{ color: '#aaa' }} }},
    series: [{{
      type: 'bar',
      data: allDeltas.map(function(v, i) {{
        return {{ value: v, itemStyle: {{ color: dColors[i] }} }};
      }}),
      markLine: {{
        silent: true,
        lineStyle: {{ color: '#888', type: 'dashed' }},
        data: [{{ yAxis: 0 }}]
      }}
    }}]
  }});
  window.addEventListener('resize', () => dChart.resize());

  document.getElementById('analysis-{sid}').scrollIntoView({{ behavior: 'smooth' }});
}})();
</script>
"""

BASE_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>F1 2026 — Chinese Grand Prix Race</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
  <style>
    body { margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; }
    h1 { color: #e10600; font-size: 28px; margin-bottom: 4px; }
    .subtitle { color: #aaa; font-size: 13px; margin-bottom: 40px; }
    .container { max-width: 1400px; margin: 0 auto; }
    .analysis-section { margin-bottom: 60px; padding-bottom: 40px; border-bottom: 1px solid #333; }
    .analysis-section:last-child { border-bottom: none; }
    .section-title { font-size: 22px; font-weight: 600; color: #fff; margin-bottom: 4px; }
    .section-timestamp { color: #666; font-size: 11px; margin-bottom: 20px; }
    .chart-label { font-size: 15px; font-weight: 500; color: #ccc; margin-bottom: 10px; }
    .chart { width: 100%; height: 500px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>F1 2026 — Chinese Grand Prix Race</h1>
    <div class="subtitle">Interactive analysis dashboard</div>
    <div id="analytics-content"><!-- ANALYTICS-END --></div>
  </div>
</body>
</html>"""

MARKER = "<!-- ANALYTICS-END -->"

if out_path.exists():
    html = out_path.read_text()
    if MARKER not in html:
        html = html.replace("</div>\n  </div>\n</body>", f"{MARKER}\n    </div>\n  </div>\n</body>")
else:
    html = BASE_HTML

html = html.replace(MARKER, section + "\n    " + MARKER)
out_path.write_text(html)

print(f"\n✓ Dashboard written → {out_path}")
