"""
build_report.py — Inline run-log JSON data into benchmark_report.html.

Replaces both fetch() loaders with synchronous inline JS variables so the
report works when opened directly as a file (file://) — no HTTP server needed.
Also works on GitHub Pages (static hosting).

Usage:
    python scripts/build_report.py

Reads:
    evolve_sys/benchmark_report.html           (template)
    evolve_sys/run_log_attractor.json
    evolve_sys_baseline/run_log_baseline.json

Writes:
    evolve_sys/benchmark_report.html           (in-place, self-contained)
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HTML_PATH    = os.path.join(ROOT, "evolve_sys", "benchmark_report.html")
AF_LOG_PATH  = os.path.join(ROOT, "evolve_sys", "run_log_attractor.json")
BL_LOG_PATH  = os.path.join(ROOT, "evolve_sys_baseline", "run_log_baseline.json")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def normalize(data):
    """Return plain list of cycle dicts from either list or {cycles:[...]}."""
    if isinstance(data, list):
        return data
    return data.get("cycles", [])


def build():
    # ── Load data ─────────────────────────────────────────────────────────────
    af_raw = load_json(AF_LOG_PATH)
    bl_raw = load_json(BL_LOG_PATH)
    a_cycles = normalize(af_raw)
    b_cycles = normalize(bl_raw)

    a_json = json.dumps(a_cycles, separators=(',', ':'))
    b_json = json.dumps(b_cycles, separators=(',', ':'))

    # ── Read HTML ─────────────────────────────────────────────────────────────
    with open(HTML_PATH, encoding="utf-8") as f:
        html = f.read()

    # ── Replace global data loader (onRunData section) ────────────────────────
    # Find the block between <!-- ─── Global Data Loader ─── --> and </script>
    LOADER_START = "<!-- ─── Global Data Loader ─── -->"
    LOADER_SCRIPT_OPEN = "<script>"

    inline_loader = f"""<!-- ─── Global Data Loader ─── -->
<script>
window._runData = null;
window._runDataCbs = [];

function onRunData(cb) {{
  if (window._runData) {{ cb(window._runData); return; }}
  window._runDataCbs.push(cb);
}}

// Data inlined at build time by scripts/build_report.py — works with file://, GitHub Pages, anywhere.
(function() {{
  var aCycles = {a_json};
  var bCycles = {b_json};
  window._runData = {{ bCycles: bCycles, aCycles: aCycles }};
  (window._runDataCbs || []).forEach(function(cb) {{ cb(window._runData); }});
  window._runDataCbs = null;
  var statusEl = document.getElementById('cmp-load-status');
  if (statusEl) statusEl.innerHTML = '<span style="color:#22c55e">✓ Data inlined at build time (standalone HTML)</span>';
}})();
</script>"""

    # Match from the LOADER_START comment through the closing </script>
    pattern = re.compile(
        r'<!-- ─── Global Data Loader ─── -->.*?</script>',
        re.DOTALL
    )
    if not pattern.search(html):
        print("ERROR: Could not find '<!-- ─── Global Data Loader ─── -->' block", file=sys.stderr)
        sys.exit(1)
    html = pattern.sub(lambda _: inline_loader, html, count=1)

    # ── Replace the comparison section's separate loadAndRender() fetch ───────
    # This function has its own fetch() calls; wire it to the already-loaded _runData.
    # Replace the fetch-based loadAndRender with a version that reads window._runData
    # Match both async (original) and sync (already-built) versions
    LOAD_AND_RENDER_PATTERN = re.compile(
        r'// ── Load both run logs and render everything ─+\n  (?:async )?function loadAndRender\(\) \{.*?\n  \}',
        re.DOTALL
    )
    inline_render = (
        "// ── Load both run logs and render everything ──────────────────────────────\n"
        "  function loadAndRender() {\n"
        "    // Use data already inlined by scripts/build_report.py\n"
        "    if (!window._runData) { onRunData(function() { loadAndRender(); }); return; }\n"
        "    const status = document.getElementById('cmp-load-status');\n"
        "    const normalize = d => Array.isArray(d) ? d : (d.cycles || []);\n"
        "    const g  = buildSeries(normalize(window._runData.bCycles));\n"
        "    const af = buildSeries(normalize(window._runData.aCycles));\n"
        "    updateTable(g, af);\n"
        "    updateHero(g, af);\n"
        "    if (status) status.innerHTML = '<span style=\"color:#22c55e\">"
        "\u2713 Data inlined at build time (standalone HTML)</span>';\n"
        "    window._cmpData = { labels: ['Start', ...normalize(window._runData.aCycles)"
        ".map((_, i) => 'C'+(i+1))], greedy: g, attractor: af, targets: TARGETS };\n"
        "    drawAll();\n"
        "  }"
    )

    if LOAD_AND_RENDER_PATTERN.search(html):
        html = LOAD_AND_RENDER_PATTERN.sub(lambda _: inline_render, html, count=1)
    else:
        print("WARNING: Could not find loadAndRender block — comparison charts may not render", file=sys.stderr)

    # ── Write back ────────────────────────────────────────────────────────────
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Built: {HTML_PATH}")
    print(f"  AF cycles:       {len(a_cycles)}")
    print(f"  Baseline cycles: {len(b_cycles)}")
    print(f"  File size:       {len(html):,} bytes")
    print("  Open directly in any browser — no server needed.")


if __name__ == "__main__":
    build()
