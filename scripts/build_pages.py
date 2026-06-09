#!/usr/bin/env python3
"""Build the GitHub Pages site for F1 2026 analyses.

Scans ``visualizations/*.html`` (the interactive dashboards produced by the
f1-analytics workflow), copies them into ``docs/`` (the folder GitHub Pages
serves from in "Deploy from a branch" mode), and generates a landing
``docs/index.html`` that lists and links to each one. The index is derived from
the dashboards on every build, so it stays current as new analyses are added.

Run this after adding/updating a dashboard, then commit ``docs/``:

    python3 scripts/build_pages.py && git add docs && git commit -m "rebuild site"
"""

import html
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "visualizations"
OUT = ROOT / "docs"

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
TITLE_PREFIX = re.compile(r"^\s*F1\s*2026\s*[—\-–:]\s*", re.IGNORECASE)
# Relative data files a dashboard loads at runtime (e.g. fetch('../analysis/x.json')).
ASSET_RE = re.compile(r"""['"]([^'":?]+\.(?:json|csv|geojson))(?:\?[^'"]*)?['"]""",
                      re.IGNORECASE)


def read_title(path: Path) -> str:
    """Return a human-readable title for a dashboard file."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = TITLE_RE.search(text)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        title = TITLE_PREFIX.sub("", title).strip()
        if title:
            return html.unescape(title)
    return path.stem.replace("-", " ").title()


def event_key(title: str) -> str:
    """Group dashboards by event/grand prix for the index layout."""
    match = re.search(r"(.*?Grand Prix)", title, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if re.search(r"pre[\s-]*season", title, re.IGNORECASE):
        return "Pre-Season Testing"
    return "Other Analyses"


def build():
    if not SRC.is_dir():
        raise SystemExit(f"No visualizations directory found at {SRC}")

    dashboards = sorted(SRC.glob("*.html"))
    if not dashboards:
        raise SystemExit(f"No dashboards found in {SRC}")

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "visualizations").mkdir(parents=True)

    # Tell GitHub Pages to serve files as-is (skip Jekyll processing).
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    cards = []
    copied_assets = 0
    for path in dashboards:
        text = path.read_text(encoding="utf-8", errors="ignore")
        shutil.copy2(path, OUT / "visualizations" / path.name)
        copied_assets += copy_assets(text)
        title = read_title(path)
        cards.append(
            {
                "title": title,
                "href": f"visualizations/{path.name}",
                "file": path.name,
                "event": event_key(title),
            }
        )

    groups: dict[str, list[dict]] = {}
    for card in cards:
        groups.setdefault(card["event"], []).append(card)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (OUT / "index.html").write_text(render_index(groups, generated, len(cards)),
                                    encoding="utf-8")
    print(f"Built {OUT/'index.html'} with {len(cards)} dashboard(s); "
          f"copied {copied_assets} data file(s).")


def copy_assets(html_text: str) -> int:
    """Copy relative data files a dashboard fetches into docs/, preserving paths.

    Dashboards live in ``visualizations/`` and fetch data via paths relative to
    that folder (e.g. ``../analysis/x.json``). The copied dashboard lives in
    ``docs/visualizations/``, so mirroring the same relative path under
    ``docs/`` keeps those fetches working on GitHub Pages.
    """
    copied = 0
    seen: set[str] = set()
    for ref in ASSET_RE.findall(html_text):
        if ref in seen or ref.startswith(("http://", "https://", "//", "data:")):
            continue
        seen.add(ref)
        src_file = (SRC / ref).resolve()
        # Stay within the repo; ignore anything that escapes it.
        if ROOT not in src_file.parents and src_file != ROOT:
            continue
        if not src_file.is_file():
            print(f"  warning: referenced data file not found: {ref}")
            continue
        dest = Path(os.path.normpath(OUT / "visualizations" / ref))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest)
        copied += 1
    return copied


def render_index(groups: dict[str, list[dict]], generated: str, count: int) -> str:
    sections = []
    for event in sorted(groups):
        items = "\n".join(
            f"""        <a class="card" href="{html.escape(c['href'])}">
          <span class="card-title">{html.escape(c['title'])}</span>
          <span class="card-file">{html.escape(c['file'])}</span>
        </a>"""
            for c in sorted(groups[event], key=lambda c: c["title"])
        )
        sections.append(
            f"""      <section class="event">
        <h2>{html.escape(event)}</h2>
        <div class="grid">
{items}
        </div>
      </section>"""
        )

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>F1 2026 — Analysis Dashboards</title>
  <style>
    :root {{ --red: #e10600; --bg: #1a1a2e; --card: #24243e; --muted: #8a8aa3; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: #eee; }}
    header {{ padding: 48px 24px 24px; max-width: 1200px; margin: 0 auto; }}
    h1 {{ color: var(--red); font-size: 34px; margin: 0 0 6px; }}
    .lede {{ color: var(--muted); font-size: 15px; margin: 0; }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 0 24px 64px; }}
    .event {{ margin-top: 40px; }}
    .event h2 {{ font-size: 20px; color: #fff; border-bottom: 1px solid #333; padding-bottom: 8px; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }}
    .card {{ display: flex; flex-direction: column; gap: 8px; background: var(--card); border: 1px solid #33334e; border-left: 3px solid var(--red); border-radius: 10px; padding: 18px 20px; text-decoration: none; color: inherit; transition: transform .12s ease, border-color .12s ease, background .12s ease; }}
    .card:hover {{ transform: translateY(-2px); border-color: var(--red); background: #2c2c4a; }}
    .card-title {{ font-size: 16px; font-weight: 600; color: #fff; }}
    .card-file {{ font-size: 12px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .about {{ background: var(--card); border: 1px solid #33334e; border-radius: 10px; padding: 20px 24px; margin-top: 8px; }}
    .about h2 {{ font-size: 18px; color: #fff; margin: 0 0 10px; }}
    .about p {{ color: #cfcfe0; font-size: 14px; line-height: 1.6; margin: 0 0 12px; }}
    .about ul {{ color: #cfcfe0; font-size: 14px; line-height: 1.6; margin: 0; padding-left: 20px; }}
    .about li {{ margin-bottom: 6px; }}
    .about strong {{ color: #fff; }}
    footer {{ max-width: 1200px; margin: 0 auto; padding: 24px; color: #555; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>F1 2026 — Analysis Dashboards</h1>
    <p class="lede">{count} interactive dashboard{'s' if count != 1 else ''}. Click any card to open the full analysis.</p>
  </header>
  <main>
    <section class="about">
      <h2>About these analyses</h2>
      <p>Each card below opens a self-contained, interactive dashboard for a single F1 2026 session
      — built from real telemetry and timing data (lap times, sector splits, speed/throttle/brake
      traces, tyre stints, weather and race-control events). The charts dig into specific questions
      like braking performance, pace degradation and head-to-head driver comparisons.</p>
      <p><strong>How to navigate &amp; view an analysis:</strong></p>
      <ul>
        <li>Dashboards are grouped by Grand Prix. <strong>Click any card</strong> to open its full analysis.</li>
        <li>Charts are <strong>interactive</strong>: hover for exact values, click legend entries to toggle drivers/series, and drag to zoom into a lap range.</li>
        <li>Use each chart's <strong>toolbox</strong> (top-right icons) to restore the zoom or save the chart as an image.</li>
        <li>Use your browser's <strong>Back</strong> button to return here and pick another session.</li>
      </ul>
    </section>
{body}
  </main>
  <footer>Generated {generated} · built from <code>visualizations/</code></footer>
</body>
</html>
"""


if __name__ == "__main__":
    build()
