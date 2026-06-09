import json
import pandas as pd
from datetime import datetime

base = "/Users/garyhukkeri/CodeSpace/p-projects/f1"

with open(f"{base}/Australian Grand Prix/Race/HAM/laptimes.json") as f:
    aus = pd.DataFrame(json.load(f))
with open(f"{base}/Chinese Grand Prix/Race/HAM/laptimes.json") as f:
    chn = pd.DataFrame(json.load(f))

def clean(df):
    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    df["s1"] = pd.to_numeric(df["s1"], errors="coerce")
    df["s2"] = pd.to_numeric(df["s2"], errors="coerce")
    df["s3"] = pd.to_numeric(df["s3"], errors="coerce")
    df["pos"] = pd.to_numeric(df["pos"], errors="coerce")
    return df

aus = clean(aus)
chn = clean(chn)

aus_valid = aus[(aus["del"] == False) & (aus["iacc"] == True)]
chn_valid = chn[(chn["del"] == False) & (chn["iacc"] == True)]

aus_best = aus_valid["time"].min()
aus_mean = aus_valid["time"].mean()
aus_median = aus_valid["time"].median()
chn_best = chn_valid["time"].min()
chn_mean = chn_valid["time"].mean()
chn_median = chn_valid["time"].median()

aus_best_s1 = aus_valid["s1"].min()
aus_best_s2 = aus_valid["s2"].min()
aus_best_s3 = aus_valid["s3"].min()
chn_best_s1 = chn_valid["s1"].min()
chn_best_s2 = chn_valid["s2"].min()
chn_best_s3 = chn_valid["s3"].min()

aus_laps = aus["lap"].tolist()
aus_times = [None if pd.isna(t) else round(t, 3) for t in aus["time"]]
chn_laps = chn["lap"].tolist()
chn_times = [None if pd.isna(t) else round(t, 3) for t in chn["time"]]

aus_positions = [None if pd.isna(p) else int(p) for p in aus["pos"]]
chn_positions = [None if pd.isna(p) else int(p) for p in chn["pos"]]

aus_compounds = aus["compound"].tolist()
chn_compounds = chn["compound"].tolist()
aus_stints = aus["stint"].tolist()
chn_stints = chn["stint"].tolist()

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
ts_id = datetime.now().strftime("%Y%m%d-%H%M%S")

html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>F1 2026 — HAM: Australian GP vs Chinese GP Race Comparison</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
  <style>
    body {{ margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; }}
    h1 {{ color: #e10600; font-size: 28px; margin-bottom: 4px; }}
    .subtitle {{ color: #aaa; font-size: 13px; margin-bottom: 40px; }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    .analysis-section {{ margin-bottom: 60px; padding-bottom: 40px; border-bottom: 1px solid #333; }}
    .analysis-section:last-child {{ border-bottom: none; }}
    .section-title {{ font-size: 22px; font-weight: 600; color: #fff; margin-bottom: 4px; }}
    .section-timestamp {{ color: #666; font-size: 11px; margin-bottom: 20px; }}
    .chart {{ width: 100%; height: 500px; }}
    .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
    .stat-card {{ background: #16213e; border-radius: 12px; padding: 20px; border: 1px solid #333; }}
    .stat-card h3 {{ margin: 0 0 16px 0; color: #e10600; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
    .stat-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #222; }}
    .stat-row:last-child {{ border-bottom: none; }}
    .stat-label {{ color: #888; font-size: 13px; }}
    .stat-value {{ font-weight: 600; font-size: 14px; }}
    .aus {{ color: #22d3ee; }}
    .chn {{ color: #f59e0b; }}
    .better {{ color: #4ade80; }}
    .worse {{ color: #f87171; }}
    .chart-row {{ display: flex; gap: 20px; flex-wrap: wrap; }}
    .chart-half {{ flex: 1; min-width: 400px; height: 500px; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>HAM — Australian GP vs Chinese GP Race</h1>
    <div class="subtitle">Lewis Hamilton performance comparison &middot; Generated: {now}</div>
    <div id="analytics-content">

<!-- Key Stats -->
<div class="analysis-section">
  <div class="section-title">Key Race Stats</div>
  <div class="stats-grid">
    <div class="stat-card">
      <h3>Race Overview</h3>
      <div class="stat-row"><span class="stat-label">Race</span><span class="stat-value aus">Australian GP</span></div>
      <div class="stat-row"><span class="stat-label">Laps</span><span class="stat-value">{len(aus_laps)}</span></div>
      <div class="stat-row"><span class="stat-label">Finish Position</span><span class="stat-value">P{int(aus['pos'].dropna().iloc[-1])}</span></div>
      <div class="stat-row"><span class="stat-label">Strategy</span><span class="stat-value">MED (28) &rarr; HARD (30)</span></div>
      <div class="stat-row"><span class="stat-label">Pit Stops</span><span class="stat-value">1</span></div>
    </div>
    <div class="stat-card">
      <h3>Race Overview</h3>
      <div class="stat-row"><span class="stat-label">Race</span><span class="stat-value chn">Chinese GP</span></div>
      <div class="stat-row"><span class="stat-label">Laps</span><span class="stat-value">{len(chn_laps)}</span></div>
      <div class="stat-row"><span class="stat-label">Finish Position</span><span class="stat-value">P{int(chn['pos'].dropna().iloc[-1])}</span></div>
      <div class="stat-row"><span class="stat-label">Strategy</span><span class="stat-value">MED (9) &rarr; HARD (46)</span></div>
      <div class="stat-row"><span class="stat-label">Pit Stops</span><span class="stat-value">1</span></div>
    </div>
    <div class="stat-card">
      <h3>Lap Times (clean laps)</h3>
      <div class="stat-row"><span class="stat-label"></span><span class="stat-value"><span class="aus">AUS</span> / <span class="chn">CHN</span></span></div>
      <div class="stat-row"><span class="stat-label">Best Lap</span><span class="stat-value"><span class="aus">{aus_best:.3f}s</span> / <span class="chn">{chn_best:.3f}s</span></span></div>
      <div class="stat-row"><span class="stat-label">Average</span><span class="stat-value"><span class="aus">{aus_mean:.3f}s</span> / <span class="chn">{chn_mean:.3f}s</span></span></div>
      <div class="stat-row"><span class="stat-label">Median</span><span class="stat-value"><span class="aus">{aus_median:.3f}s</span> / <span class="chn">{chn_median:.3f}s</span></span></div>
      <div class="stat-row"><span class="stat-label">Clean Laps</span><span class="stat-value"><span class="aus">{len(aus_valid)}</span> / <span class="chn">{len(chn_valid)}</span></span></div>
    </div>
    <div class="stat-card">
      <h3>Best Sectors (clean laps)</h3>
      <div class="stat-row"><span class="stat-label"></span><span class="stat-value"><span class="aus">AUS</span> / <span class="chn">CHN</span></span></div>
      <div class="stat-row"><span class="stat-label">Sector 1</span><span class="stat-value"><span class="aus">{aus_best_s1:.3f}s</span> / <span class="chn">{chn_best_s1:.3f}s</span></span></div>
      <div class="stat-row"><span class="stat-label">Sector 2</span><span class="stat-value"><span class="aus">{aus_best_s2:.3f}s</span> / <span class="chn">{chn_best_s2:.3f}s</span></span></div>
      <div class="stat-row"><span class="stat-label">Sector 3</span><span class="stat-value"><span class="aus">{aus_best_s3:.3f}s</span> / <span class="chn">{chn_best_s3:.3f}s</span></span></div>
    </div>
  </div>
</div>

<!-- Lap Time Progression -->
<div class="analysis-section" id="laptimes-{ts_id}">
  <div class="section-title">Lap Time Progression</div>
  <div class="section-timestamp">Generated: {now}</div>
  <div id="chart-laptimes" class="chart"></div>
</div>
<script>
(function() {{
  var chart = echarts.init(document.getElementById('chart-laptimes'), 'dark');
  chart.setOption({{
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
    toolbox: {{ feature: {{ saveAsImage: {{ title: 'Save' }}, dataZoom: {{ title: {{ zoom: 'Zoom', back: 'Reset' }} }} }}, right: 20 }},
    legend: {{ data: ['Australian GP', 'Chinese GP'], top: 10 }},
    xAxis: {{ type: 'value', name: 'Lap', nameLocation: 'center', nameGap: 30, min: 1 }},
    yAxis: {{ type: 'value', name: 'Lap Time (s)', nameLocation: 'center', nameGap: 50,
              splitLine: {{ lineStyle: {{ color: '#333' }} }} }},
    dataZoom: [{{ type: 'inside' }}, {{ type: 'slider' }}],
    grid: {{ left: 70, right: 40, bottom: 80, top: 50 }},
    series: [
      {{
        name: 'Australian GP', type: 'line', symbol: 'circle', symbolSize: 5,
        lineStyle: {{ color: '#22d3ee' }}, itemStyle: {{ color: '#22d3ee' }},
        data: {[[l, t] for l, t in zip(aus_laps, aus_times) if t is not None]}
      }},
      {{
        name: 'Chinese GP', type: 'line', symbol: 'diamond', symbolSize: 5,
        lineStyle: {{ color: '#f59e0b' }}, itemStyle: {{ color: '#f59e0b' }},
        data: {[[l, t] for l, t in zip(chn_laps, chn_times) if t is not None]}
      }}
    ]
  }});
  window.addEventListener('resize', () => chart.resize());
}})();
</script>

<!-- Position Progression -->
<div class="analysis-section" id="positions-{ts_id}">
  <div class="section-title">Position Progression</div>
  <div class="section-timestamp">Generated: {now}</div>
  <div id="chart-positions" class="chart"></div>
</div>
<script>
(function() {{
  var chart = echarts.init(document.getElementById('chart-positions'), 'dark');
  chart.setOption({{
    tooltip: {{ trigger: 'axis' }},
    toolbox: {{ feature: {{ saveAsImage: {{ title: 'Save' }} }}, right: 20 }},
    legend: {{ data: ['Australian GP', 'Chinese GP'], top: 10 }},
    xAxis: {{ type: 'value', name: 'Lap', nameLocation: 'center', nameGap: 30, min: 1 }},
    yAxis: {{ type: 'value', name: 'Position', nameLocation: 'center', nameGap: 40,
              inverse: true, min: 1, max: 10,
              splitLine: {{ lineStyle: {{ color: '#333' }} }} }},
    grid: {{ left: 60, right: 40, bottom: 50, top: 50 }},
    series: [
      {{
        name: 'Australian GP', type: 'line', step: 'end', symbol: 'none',
        lineStyle: {{ color: '#22d3ee', width: 2 }}, areaStyle: {{ color: 'rgba(34,211,238,0.08)' }},
        data: {[[l, p] for l, p in zip(aus_laps, aus_positions) if p is not None]}
      }},
      {{
        name: 'Chinese GP', type: 'line', step: 'end', symbol: 'none',
        lineStyle: {{ color: '#f59e0b', width: 2 }}, areaStyle: {{ color: 'rgba(245,158,11,0.08)' }},
        data: {[[l, p] for l, p in zip(chn_laps, chn_positions) if p is not None]}
      }}
    ]
  }});
  window.addEventListener('resize', () => chart.resize());
}})();
</script>

<!-- Tire Strategy -->
<div class="analysis-section" id="strategy-{ts_id}">
  <div class="section-title">Tire Strategy</div>
  <div class="section-timestamp">Generated: {now}</div>
  <div class="chart-row">
    <div id="chart-strat-aus" class="chart-half"></div>
    <div id="chart-strat-chn" class="chart-half"></div>
  </div>
</div>
<script>
(function() {{
  var compoundColor = {{ SOFT: '#e10600', MEDIUM: '#f5c542', HARD: '#ddd', INTERMEDIATE: '#39b54a', WET: '#0071c5' }};

  // Australian GP stints
  var ausChart = echarts.init(document.getElementById('chart-strat-aus'), 'dark');
  ausChart.setOption({{
    title: {{ text: 'Australian GP', left: 'center', top: 10, textStyle: {{ fontSize: 15, color: '#22d3ee' }} }},
    tooltip: {{ formatter: function(p) {{ return 'Stint ' + (p.dataIndex+1) + ': ' + p.name + '<br/>Laps: ' + p.value; }} }},
    toolbox: {{ feature: {{ saveAsImage: {{ title: 'Save' }} }}, right: 10 }},
    xAxis: {{ type: 'category', data: ['MEDIUM', 'HARD'],
              axisLabel: {{ color: '#ccc' }} }},
    yAxis: {{ type: 'value', name: 'Laps', splitLine: {{ lineStyle: {{ color: '#333' }} }} }},
    grid: {{ left: 60, right: 30, bottom: 40, top: 60 }},
    series: [{{
      type: 'bar', barWidth: '50%',
      data: [
        {{ value: 28, name: 'MEDIUM', itemStyle: {{ color: compoundColor.MEDIUM }} }},
        {{ value: 30, name: 'HARD', itemStyle: {{ color: compoundColor.HARD }} }}
      ],
      label: {{ show: true, position: 'top', color: '#fff', fontSize: 14, fontWeight: 'bold',
                formatter: function(p) {{ return p.value + ' laps'; }} }}
    }}]
  }});

  // Chinese GP stints
  var chnChart = echarts.init(document.getElementById('chart-strat-chn'), 'dark');
  chnChart.setOption({{
    title: {{ text: 'Chinese GP', left: 'center', top: 10, textStyle: {{ fontSize: 15, color: '#f59e0b' }} }},
    tooltip: {{ formatter: function(p) {{ return 'Stint ' + (p.dataIndex+1) + ': ' + p.name + '<br/>Laps: ' + p.value; }} }},
    toolbox: {{ feature: {{ saveAsImage: {{ title: 'Save' }} }}, right: 10 }},
    xAxis: {{ type: 'category', data: ['MEDIUM', 'HARD'],
              axisLabel: {{ color: '#ccc' }} }},
    yAxis: {{ type: 'value', name: 'Laps', splitLine: {{ lineStyle: {{ color: '#333' }} }} }},
    grid: {{ left: 60, right: 30, bottom: 40, top: 60 }},
    series: [{{
      type: 'bar', barWidth: '50%',
      data: [
        {{ value: 9, name: 'MEDIUM', itemStyle: {{ color: compoundColor.MEDIUM }} }},
        {{ value: 46, name: 'HARD', itemStyle: {{ color: compoundColor.HARD }} }}
      ],
      label: {{ show: true, position: 'top', color: '#fff', fontSize: 14, fontWeight: 'bold',
                formatter: function(p) {{ return p.value + ' laps'; }} }}
    }}]
  }});

  window.addEventListener('resize', () => {{ ausChart.resize(); chnChart.resize(); }});
}})();
</script>

<!-- Lap Time Consistency (box plot style via scatter) -->
<div class="analysis-section" id="consistency-{ts_id}">
  <div class="section-title">Lap Time Consistency (Clean Laps)</div>
  <div class="section-timestamp">Generated: {now}</div>
  <div id="chart-consistency" class="chart" style="height:450px;"></div>
</div>
<script>
(function() {{
  var ausValid = {sorted([round(t, 3) for t in aus_valid['time'].tolist()])};
  var chnValid = {sorted([round(t, 3) for t in chn_valid['time'].tolist()])};

  var chart = echarts.init(document.getElementById('chart-consistency'), 'dark');
  chart.setOption({{
    tooltip: {{ trigger: 'item' }},
    toolbox: {{ feature: {{ saveAsImage: {{ title: 'Save' }} }}, right: 20 }},
    legend: {{ data: ['Australian GP', 'Chinese GP'], top: 10 }},
    xAxis: {{ type: 'category', data: ['Australian GP', 'Chinese GP'],
              axisLabel: {{ color: '#ccc', fontSize: 14 }} }},
    yAxis: {{ type: 'value', name: 'Lap Time (s)',
              splitLine: {{ lineStyle: {{ color: '#333' }} }} }},
    grid: {{ left: 70, right: 40, bottom: 40, top: 50 }},
    series: [
      {{
        name: 'Australian GP', type: 'scatter',
        data: ausValid.map(function(v) {{ return [0, v]; }}),
        itemStyle: {{ color: 'rgba(34,211,238,0.5)' }}, symbolSize: 8
      }},
      {{
        name: 'Chinese GP', type: 'scatter',
        data: chnValid.map(function(v) {{ return [1, v]; }}),
        itemStyle: {{ color: 'rgba(245,158,11,0.5)' }}, symbolSize: 8
      }},
      {{
        type: 'boxplot', name: 'Distribution',
        data: [ausValid, chnValid],
        itemStyle: {{ borderColor: '#fff', borderWidth: 1 }}
      }}
    ]
  }});
  window.addEventListener('resize', () => chart.resize());
}})();
</script>

    </div>
  </div>
</body>
</html>"""

out_path = f"{base}/visualizations/ham-aus-vs-chn-race.html"
with open(out_path, "w") as f:
    f.write(html)

print(f"Dashboard written to {out_path}")
print(f"\nAustralian GP: {len(aus_laps)} laps, finished P{int(aus['pos'].dropna().iloc[-1])}, best {aus_best:.3f}s, avg {aus_mean:.3f}s")
print(f"Chinese GP:    {len(chn_laps)} laps, finished P{int(chn['pos'].dropna().iloc[-1])}, best {chn_best:.3f}s, avg {chn_mean:.3f}s")
