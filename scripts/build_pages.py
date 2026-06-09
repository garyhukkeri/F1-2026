#!/usr/bin/env python3
"""Build the GitHub Pages site for F1 2026 analyses.

Scans ``visualizations/*.html`` (the interactive dashboards produced by the
f1-analytics workflow), copies them into the output directory, and generates a
landing ``index.html`` that lists and links to each one. The index is derived
from the dashboards on every build, so it stays current as new analyses are
added — no manual editing required.
"""

import html
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "visualizations"
OUT = ROOT / "_site"

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
TITLE_PREFIX = re.compile(r"^\s*F1\s*2026\s*[—\-–:]\s*", re.IGNORECASE)


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

    cards = []
    for path in dashboards:
        shutil.copy2(path, OUT / "visualizations" / path.name)
        cards.append(
            {
                "title": read_title(path),
                "href": f"visualizations/{path.name}",
                "file": path.name,
                "event": event_key(read_title(path)),
            }
        )

    groups: dict[str, list[dict]] = {}
    for card in cards:
        groups.setdefault(card["event"], []).append(card)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (OUT / "index.html").write_text(render_index(groups, generated, len(cards)),
                                    encoding="utf-8")
    print(f"Built {OUT/'index.html'} with {len(cards)} dashboard(s).")


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
    footer {{ max-width: 1200px; margin: 0 auto; padding: 24px; color: #555; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>F1 2026 — Analysis Dashboards</h1>
    <p class="lede">{count} interactive dashboard{'s' if count != 1 else ''}. Click any card to open the full analysis.</p>
  </header>
  <main>
{body}
  </main>
  <footer>Generated {generated} · built from <code>visualizations/</code></footer>
</body>
</html>
"""


if __name__ == "__main__":
    build()
