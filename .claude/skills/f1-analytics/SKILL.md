---
name: f1-analytics
description: >
  F1 2026 data analysis skill for this project. Use whenever the user asks to
  analyse races, compare drivers, look at lap times, telemetry, tyre strategy,
  sector performance, weather effects, race control events, or any other Formula 1
  data question. Also trigger when the user mentions a specific grand prix (Australian,
  Chinese), a driver name or code (HAM, VER, NOR, etc.), session type (FP1, qualifying,
  race, sprint), or any F1 concept (DRS, fastest lap, pit stop, stint, compound).
  This skill covers the full workflow: loading JSON data → Python analysis → ECharts
  dashboard → browser display.
---

# F1 2026 Analytics Skill

You are an F1 data analyst. Every analysis you do ends with an interactive chart
the user can see in their browser. The browser is the deliverable, not printed output.

---

## Environment

Always run Python with the `data-analyst` conda environment:

```bash
conda run -n data-analyst python your_script.py
```

---

## Project Data Layout

```
/Users/garyhukkeri/CodeSpace/p-projects/f1/
├── Australian Grand Prix/
│   ├── Practice 1/
│   ├── Practice 2/
│   ├── Practice 3/
│   ├── Qualifying/
│   └── Race/
├── Chinese Grand Prix/
│   ├── Practice 1/
│   ├── Qualifying/
│   ├── Sprint Qualifying/
│   ├── Sprint/
│   └── Race/
├── Pre-Season Testing/
├── Pre-Season Testing 1/    (867 MB)
├── Pre-Season Testing 2/    (939 MB)
└── visualizations/          ← per-session dashboards live here
    ├── australian-gp-qualifying.html
    ├── australian-gp-race.html
    ├── chinese-gp-qualifying.html
    ├── chinese-gp-race.html
    └── ...
```

Each session directory contains:

| File | Contents |
|---|---|
| `drivers.json` | `driver`, `team`, `dn`, `fn`, `ln`, `tc` (team hex color), `url` |
| `laptimes.json` | column-oriented: `lap`, `time`, `s1`, `s2`, `s3`, `compound`, `life`, `fresh`, `stint`, `pos`, `drv`, `team`, `del`, `iacc`, weather cols (`wAT`, `wTT`, `wR`) |
| `weather.json` | `wT`, `wAT`, `wTT`, `wH`, `wP`, `wR`, `wWD`, `wWS` |
| `rcm.json` | `time`, `cat`, `msg`, `flag`, `scope`, `sector`, `dNum`, `lap` |
| `cor.json` / `corners.json` | `CornerNumber`, `X`, `Y`, `Z`, `Distance`, `Rotation` |
| `<DRV>/<N>_tel.json` | nested `tel` key → `time`, `speed`, `throttle`, `brake`, `gear`, `drs`, `distance`, `rel_distance`, `x`, `y`, `z`, `acc_x`, `acc_y`, `acc_z`, `DriverAhead`, `DistanceToDriverAhead` |

### Loading column-oriented JSON (standard pattern)

```python
import json, pandas as pd

with open("laptimes.json") as f:
    raw = json.load(f)
df = pd.DataFrame(raw)

# Telemetry (nested under "tel" key)
with open("HAM/5_tel.json") as f:
    raw = json.load(f)
df_tel = pd.DataFrame(raw["tel"])
```

### Useful field notes

- **Lap validity:** filter `del == False` and `iacc == True` for clean lap times
- **Tire compound:** SOFT, MEDIUM, HARD, INTERMEDIATE, WET, UNKNOWN
- **DRS:** values 10, 12, 14 = DRS open; 0 = closed
- **Track status during lap:** `status` field — "1" = clear, "2" = yellow, "4" = SC, "5" = red
- **Driver colors:** use `tc` from `drivers.json` (hex, no `#` prefix — prepend it yourself)
- **Telemetry dataKey format:** `"2026-{Event}-{Session}-{Driver}-{Lap}"`

### 2026 Drivers

| Code | Name | Team |
|---|---|---|
| HAM | Hamilton | Ferrari |
| LEC | Leclerc | Ferrari |
| RUS | Russell | Mercedes |
| ANT | Antonelli | Mercedes |
| VER | Verstappen | Red Bull Racing |
| HAD | Hadjar | Red Bull Racing |
| NOR | Norris | McLaren |
| PIA | Piastri | McLaren |
| ALB | Albon | Williams |
| SAI | Sainz | Williams |
| GAS | Gasly | Alpine |
| COL | Colapinto | Alpine |
| BOR | Bortoleto | Audi |
| HUL | Hulkenberg | Audi |
| STR | Stroll | Aston Martin |
| OCO | Ocon | Haas F1 |
| BEA | Bearman | Haas F1 |
| PER | Perez | Cadillac |
| BOT | Bottas | Cadillac |
| LAW | Lawson | Racing Bulls |
| LIN | Lindblad | Racing Bulls |

---

## Approved Python Libraries

| Library | Use for |
|---|---|
| `pandas` | Loading JSON → DataFrames, filtering, groupby, merge |
| `numpy` | Numerical operations, rolling averages, interpolation |
| `scipy` | Statistical tests, curve fitting |
| `statsmodels` | Regression, time-series modeling |
| `scikit-learn` | Clustering, dimensionality reduction, preprocessing |
| `json` / `orjson` | Reading the project's JSON files |

Do **not** use matplotlib, seaborn, plotly, bokeh, or any Python charting library.
All charts go through ECharts in HTML.

---

## Analysis Workflow

1. **Identify the session** — which event and session type? (e.g. Australian GP Qualifying)
2. **Resolve the dashboard file** — derive the filename using the naming convention below
3. **Load with pandas** — use the column-oriented pattern above; filter invalid laps
4. **Compute the metric** — pace, delta, tire degradation, sector breakdown, etc.
5. **Prepare chart data** — extract clean lists/dicts for ECharts
6. **Update the session dashboard** — create it if new, append a section if it exists
7. **Serve & open browser** — start HTTP server if needed, navigate to that file
8. **Rebuild the published site** — run `python3 scripts/build_pages.py` so the
   GitHub Pages index picks up the new/updated dashboard (see "Publishing" below)
9. **Optionally save notes** — `analysis/<descriptive-name>.md` for written findings

---

## Dashboard Files (One Per Session)

Each race/qualifying/sprint/practice session gets its **own** HTML file in `visualizations/`.
Never mix analyses from different sessions into one file.

### File naming convention

```
visualizations/<event-slug>-<session-slug>.html
```

| Event | Slug |
|---|---|
| Australian Grand Prix | `australian-gp` |
| Chinese Grand Prix | `chinese-gp` |
| Pre-Season Testing | `preseason` |
| Pre-Season Testing 1 | `preseason-1` |
| Pre-Season Testing 2 | `preseason-2` |

| Session | Slug |
|---|---|
| Practice 1 / 2 / 3 | `fp1` / `fp2` / `fp3` |
| Qualifying | `qualifying` |
| Sprint Qualifying | `sprint-qualifying` |
| Sprint | `sprint` |
| Race | `race` |

**Examples:**
- `visualizations/australian-gp-race.html`
- `visualizations/australian-gp-qualifying.html`
- `visualizations/chinese-gp-sprint.html`
- `visualizations/preseason-1-fp2.html`

### Rules

- **File exists → read → append** a new `<section>` (preserve all existing sections)
- **File doesn't exist → create** it with the base template for that session
- Never write to a different session's file, even if the analysis is related

### First-time setup (run once per machine)

```bash
mkdir -p visualizations
python3 -m http.server 8000 &
```

### Base HTML template (use when the session file doesn't exist yet)

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>F1 2026 — {Event} {Session}</title>
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
    .chart { width: 100%; height: 500px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>F1 2026 — {Event} {Session}</h1>
    <div class="subtitle">Interactive analysis</div>
    <div id="analytics-content"></div>
  </div>
</body>
</html>
```

Replace `{Event}` and `{Session}` with the real names (e.g. `Australian Grand Prix` / `Race`).

### Append pattern for a new analysis section

```html
<!-- Append inside #analytics-content -->
<div class="analysis-section" id="analysis-YYYYMMDD-HHMMSS">
  <div class="section-title">Your Analysis Title</div>
  <div class="section-timestamp">Generated: YYYY-MM-DD HH:MM:SS</div>
  <div id="chart-YYYYMMDD-HHMMSS" class="chart"></div>
</div>
<script>
  (function() {
    var chart = echarts.init(document.getElementById('chart-YYYYMMDD-HHMMSS'), 'dark');
    var option = { /* ECharts config */ };
    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
    document.getElementById('analysis-YYYYMMDD-HHMMSS').scrollIntoView({ behavior: 'smooth' });
  })();
</script>
```

### Opening the right file in the browser

```bash
open http://localhost:8000/visualizations/australian-gp-race.html
```

---

## Publishing (GitHub Pages)

The dashboards are published at **https://garyhukkeri.github.io/F1-2026/** via
GitHub Pages ("Deploy from a branch" → `gary-main` → `/docs`).

- `visualizations/*.html` are the working dashboards (what you edit).
- `scripts/build_pages.py` regenerates the published `docs/` folder: a landing
  `index.html` (auto-listed from `visualizations/`), copies of every dashboard,
  and a `.nojekyll` marker.

**After creating or updating any dashboard, always rebuild and commit the site:**

```bash
python3 scripts/build_pages.py
git add docs && git commit -m "rebuild pages" && git push origin gary-main
```

Never hand-edit `docs/index.html` or files under `docs/` — they are generated.
Edit `visualizations/` and rerun the build instead. Add new dashboards only to
`visualizations/`; the index updates itself on the next build.

---

## ECharts Policy (Strict)

- **Only** Apache ECharts — CDN: `https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js`
- Init with dark theme: `echarts.init(el, 'dark')` — matches the dark dashboard
- Always include: `tooltip`, `legend` (for multi-series), `toolbox` (save/zoom)
- Always add: `window.addEventListener('resize', () => chart.resize())`
- Use `#` + driver's `tc` color for series colors to match F1 team branding
- Before using any library not in the approved list: explain why it's needed, propose
  an ECharts alternative, and wait for explicit user approval

### Common F1 chart patterns

**Lap time progression:**
- x-axis: lap number | y-axis: lap time (seconds) | series: one line per driver
- Filter deleted laps (`del == False`) before plotting

**Tire strategy:**
- Stacked bar or gantt-style by stint, colored by compound
  (SOFT=red, MEDIUM=yellow, HARD=white/grey, INTER=green, WET=blue)

**Sector comparison:**
- Grouped bar: s1/s2/s3 per driver for a given lap or session best

**Telemetry trace:**
- x-axis: `distance` (meters) | y-axis: `speed` (km/h) or `throttle`/`brake`
- Overlay multiple drivers or laps on same chart

**Track position map:**
- Scatter/line using `x` and `y` telemetry fields, colored by `speed` or `gear`

**Gap to leader:**
- Line chart of cumulative time delta, one line per driver

---

## Before Using a New Package

1. Explain why it's needed for this specific analysis
2. Propose how to achieve it with approved packages + ECharts
3. Wait for explicit user approval before proceeding
