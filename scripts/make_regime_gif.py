"""
make_regime_gif.py — Render all 7 AttractorFlow regimes as an animated GIF.

Output: evolve_sys/phase_portraits.gif
Format: 1080×1080 square (optimal for LinkedIn, Twitter, Instagram)
        7 portraits in a 3+4 grid, dark theme, looping animation

Usage:
    .venv/bin/python scripts/make_regime_gif.py
"""

import math
import random
import os
from PIL import Image, ImageDraw, ImageFont

# ── Output ────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "evolve_sys", "phase_portraits.gif")

# ── Canvas / GIF settings ────────────────────────────────────────────────────
GIF_W, GIF_H = 1080, 1080      # square for LinkedIn/Twitter/Instagram
N_FRAMES     = 240              # total frames in the loop
FRAME_MS     = 50               # ms per frame → ~12 fps, 12s loop
TRAIL_LEN    = 55               # trail length matching JS

# ── Grid layout: 4 top + 3 bottom, filling available canvas ──────────────────
PAD          = 28               # outer padding
INNER_GAP    = 12               # gap between portrait cells
HEADER_H     = 80               # top title bar
FOOTER_H     = 42               # bottom tagline bar
N_COLS_TOP   = 4
N_COLS_BOT   = 3
# Cell width: constrained by 4-column top row
CELL_W = (GIF_W - 2*PAD - (N_COLS_TOP - 1)*INNER_GAP) // N_COLS_TOP
# Cell height: use ALL available vertical space for the 2-row grid
GRID_Y   = HEADER_H + PAD
GRID_BOTTOM = GIF_H - FOOTER_H - PAD
CELL_H = (GRID_BOTTOM - GRID_Y - INNER_GAP) // 2
# Portrait canvas is square (width of cell minus 4px border)
PORTRAIT_PS = CELL_W - 4
# Layout inside each cell: label, then portrait canvas, then description text
LABEL_H  = 28               # regime name row height
LABEL_PAD = 4               # padding above label

# ── Dark theme colours ────────────────────────────────────────────────────────
BG       = (8,   12,  20)        # #080c14
SURFACE  = (13,  21,  32)        # #0d1520
BORDER   = (30,  48,  80)        # #1e3050
AXIS_COL = (30,  48,  80)
TEXT_HI  = (226, 232, 240)       # #e2e8f0
TEXT_MED = (100, 116, 139)       # #64748b
BRAND    = (0,   212, 255)       # #00d4ff  (AttractorFlow cyan)

# ── Regime metadata ───────────────────────────────────────────────────────────
REGIMES = [
    {
        "id":    "CONVERGING",
        "label": "CONVERGING",
        "sub":   "λ < −0.05  ·  stable focus",
        "color": (34,  197, 94),    # #22c55e green
    },
    {
        "id":    "EXPLORING",
        "label": "EXPLORING",
        "sub":   "λ ∈ [0.05, 0.25]  ·  expansion",
        "color": (245, 158, 11),    # #f59e0b amber
    },
    {
        "id":    "STUCK",
        "label": "STUCK",
        "sub":   "λ ≈ 0  ·  fixed-point trap",
        "color": (249, 115, 22),    # #f97316 orange
    },
    {
        "id":    "OSCILLATING",
        "label": "OSCILLATING",
        "sub":   "lag-1 autocorr ≈ −1  ·  2-basin",
        "color": (251, 191, 36),    # #fbbf24 yellow
    },
    {
        "id":    "DIVERGING",
        "label": "DIVERGING",
        "sub":   "λ > 0.25  ·  scope explosion",
        "color": (239, 68,  68),    # #ef4444 red
    },
    {
        "id":    "PLATEAU",
        "label": "PLATEAU",
        "sub":   "λ ≈ −0.02  ·  marginal returns",
        "color": (168, 85,  247),   # #a855f7 purple
    },
    {
        "id":    "CYCLING",
        "label": "CYCLING",
        "sub":   "period-2 orbit  ·  healthy TDD",
        "color": (0,   212, 255),   # #00d4ff cyan
    },
]

# ── Portrait generators (Python port of JS drawFn) ────────────────────────────
# All return (x, y) in portrait-local coordinates [0..PS, 0..PS]
# or None to skip a frame.

def portrait_converging(frame, PS):
    rng = random.Random(frame * 137)
    cx = cy = PS / 2
    cycle = frame % 480
    r = PS * 0.44 * math.exp(-0.007 * cycle)
    t = cycle * 0.065
    return (
        cx + r * math.cos(t) + (rng.random() - 0.5) * 0.8,
        cy + r * math.sin(t) * 0.88 + (rng.random() - 0.5) * 0.8,
    )

def portrait_exploring(frame, PS):
    cx = cy = PS / 2
    cycle = frame % 500
    r = PS * 0.09 + PS * 0.32 * (cycle / 500)
    t = cycle * 0.055
    return (
        cx + r * math.cos(t),
        cy + r * math.sin(t * 0.95 + 0.3),
    )

def portrait_stuck(frame, PS):
    rng = random.Random(frame * 17 + 3)
    cx = cy = PS / 2
    jitter = PS * 0.11   # bigger so it's visible as a cloud
    return (
        cx + (rng.random() - 0.5) * jitter * 2,
        cy + (rng.random() - 0.5) * jitter * 2,
    )

def portrait_oscillating(frame, PS):
    rng = random.Random(frame * 31)
    Ax, Ay = PS * 0.27, PS * 0.38
    Bx, By = PS * 0.73, PS * 0.62
    DWELL, TRANSIT = 22, 8
    period = DWELL + TRANSIT
    phase = frame % (2 * period)
    if phase < DWELL:
        return (Ax + (rng.random()-0.5)*5, Ay + (rng.random()-0.5)*5)
    elif phase < DWELL + TRANSIT:
        prog = (phase - DWELL) / TRANSIT
        arc  = math.sin(prog * math.pi) * 20
        return (
            Ax + (Bx - Ax)*prog + arc*(By - Ay)/(PS*0.5),
            Ay + (By - Ay)*prog - arc*(Bx - Ax)/(PS*0.5),
        )
    elif phase < 2*DWELL + TRANSIT:
        return (Bx + (rng.random()-0.5)*5, By + (rng.random()-0.5)*5)
    else:
        prog = (phase - (2*DWELL + TRANSIT)) / TRANSIT
        arc  = math.sin(prog * math.pi) * 20
        return (
            Bx + (Ax - Bx)*prog - arc*(Ay - By)/(PS*0.5),
            By + (Ay - By)*prog + arc*(Ax - Bx)/(PS*0.5),
        )

def portrait_diverging(frame, PS):
    cx = cy = PS / 2
    cycle = frame % 160
    r = PS * 0.06 * math.exp(0.024 * cycle)
    t = cycle * 0.05
    x = cx + r * math.cos(t)
    y = cy + r * math.sin(t * 1.1)
    # clamp slightly outside canvas so trail is visible going off-edge
    return (
        max(-PS*0.15, min(PS*1.15, x)),
        max(-PS*0.15, min(PS*1.15, y)),
    )

def portrait_plateau(frame, PS):
    rng = random.Random(frame * 53)
    cx = cy = PS / 2
    t = frame * 0.038
    r = PS * 0.33 - 0.018 * (frame % 2400) + (rng.random()-0.5)*1.5
    r = max(PS * 0.05, r)
    return (
        cx + r * math.cos(t) + (rng.random()-0.5)*1.5,
        cy + r * math.sin(t) * 0.92 + (rng.random()-0.5)*1.5,
    )

def portrait_cycling(frame, PS):
    cx = cy = PS / 2
    t = frame * 0.042
    rx, ry = PS * 0.36, PS * 0.30
    return (cx + rx * math.cos(t), cy + ry * math.sin(t))


PORTRAIT_FNS = {
    "CONVERGING":  portrait_converging,
    "EXPLORING":   portrait_exploring,
    "STUCK":       portrait_stuck,
    "OSCILLATING": portrait_oscillating,
    "DIVERGING":   portrait_diverging,
    "PLATEAU":     portrait_plateau,
    "CYCLING":     portrait_cycling,
}

# ── Geometry helpers ──────────────────────────────────────────────────────────
def cell_origin(idx):
    """Top-left (x, y) of cell idx in the GIF canvas."""
    if idx < N_COLS_TOP:
        col = idx
        x = PAD + col * (CELL_W + INNER_GAP)
        y = GRID_Y
    else:
        col = idx - N_COLS_TOP
        total_w = N_COLS_BOT * CELL_W + (N_COLS_BOT - 1) * INNER_GAP
        x_off   = (GIF_W - total_w) // 2
        x = x_off + col * (CELL_W + INNER_GAP)
        y = GRID_Y + CELL_H + INNER_GAP
    return x, y

def portrait_rect(idx):
    """Return (px, py, PW, PH) — top-left and dimensions of portrait canvas."""
    cx, cy = cell_origin(idx)
    # Portrait: full cell width, fills height between label and sub-text
    px = cx + 2
    py = cy + LABEL_H + LABEL_PAD
    PW = CELL_W - 4
    SUB_H = 22   # space for sub-description text below portrait
    PH = CELL_H - LABEL_H - LABEL_PAD - SUB_H - 4
    return px, py, PW, PH

# ── Colour helpers ────────────────────────────────────────────────────────────
def lerp_color(c, alpha_frac):
    """Dim colour by alpha_frac (0=transparent, 1=full) — blend onto BG."""
    return tuple(int(BG[i] + (c[i] - BG[i]) * alpha_frac) for i in range(3))

def glow(draw, x, y, r, col, alpha=0.35):
    """Draw a soft radial glow circle."""
    for layer, a_scale in [(r*2, 0.12), (r*1.4, 0.22), (r, alpha)]:
        lc = lerp_color(col, a_scale)
        x0, y0 = x - layer, y - layer
        x1, y1 = x + layer, y + layer
        draw.ellipse([x0, y0, x1, y1], fill=lc)

# ── Font loading ──────────────────────────────────────────────────────────────
def load_font(size, bold=False):
    # Try system monospace fonts; fall back to default
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

# ── Pre-build regime trails ───────────────────────────────────────────────────
WARMUP = 120  # pre-warm: trails are visibly built-up from frame 0 of the GIF

def build_trails(n_frames, trail_len):
    """Pre-compute all trail positions for all regimes across all frames.
    Starts from WARMUP so trails are already populated from the first GIF frame."""
    trails = {r["id"]: [] for r in REGIMES}
    for regime in REGIMES:
        fn  = PORTRAIT_FNS[regime["id"]]
        # Reference size: normalised [0..200]; scaled at draw time
        PS  = 200.0
        buf = []
        total = n_frames + WARMUP
        for f in range(total):
            pt = fn(f, PS)
            buf.append(pt)
            if len(buf) > trail_len:
                buf.pop(0)
            if f >= WARMUP:
                trails[regime["id"]].append(list(buf))
    return trails

# ── Render one GIF frame ──────────────────────────────────────────────────────
def render_frame(frame_idx, trails, fonts):
    img  = Image.new("RGB", (GIF_W, GIF_H), BG)
    draw = ImageDraw.Draw(img)

    # ── Header ────────────────────────────────────────────────────────────────
    # Thin top accent line
    draw.rectangle([0, 0, GIF_W, 3], fill=BRAND)
    # Title
    title = "Phase Portraits — 7 Attractor Regimes"
    tw = draw.textlength(title, font=fonts["title"])
    draw.text(((GIF_W - tw) // 2, 14), title, font=fonts["title"], fill=TEXT_HI)
    # Subtitle
    sub = "AttractorFlow  ·  Stability-Guided Code Evolution"
    sw = draw.textlength(sub, font=fonts["sub"])
    draw.text(((GIF_W - sw) // 2, 52), sub, font=fonts["sub"], fill=TEXT_MED)

    # ── Footer ────────────────────────────────────────────────────────────────
    draw.rectangle([0, GIF_H - FOOTER_H, GIF_W, GIF_H], fill=SURFACE)
    draw.rectangle([0, GIF_H - FOOTER_H, GIF_W, GIF_H - FOOTER_H + 1], fill=BORDER)
    footer = "github.com/atprove  ·  EvolveSys autonomous code evolution engine"
    fw = draw.textlength(footer, font=fonts["footer"])
    draw.text(((GIF_W - fw) // 2, GIF_H - FOOTER_H + 14), footer,
              font=fonts["footer"], fill=TEXT_MED)

    # ── Portrait cells ─────────────────────────────────────────────────────────
    for idx, regime in enumerate(REGIMES):
        cx, cy = cell_origin(idx)
        px, py, PW, PH = portrait_rect(idx)
        col = regime["color"]
        rid = regime["id"]
        trail_now = trails[rid][frame_idx]

        # Cell background
        draw.rectangle([cx, cy, cx + CELL_W, cy + CELL_H], fill=SURFACE)
        draw.rectangle([cx, cy, cx + CELL_W - 1, cy + CELL_H - 1],
                       outline=BORDER, width=1)

        # Regime label row (coloured dot + name)
        lbl_w = draw.textlength(regime["label"], font=fonts["label"])
        dot_r = 4
        total_label_w = dot_r * 2 + 6 + lbl_w
        lbl_start_x = cx + (CELL_W - int(total_label_w)) // 2
        dot_cx_l = lbl_start_x + dot_r
        dot_cy_l = cy + LABEL_PAD + LABEL_H // 2
        draw.ellipse([dot_cx_l-dot_r, dot_cy_l-dot_r, dot_cx_l+dot_r, dot_cy_l+dot_r], fill=col)
        draw.text((lbl_start_x + dot_r*2 + 6, cy + LABEL_PAD + 2),
                  regime["label"], font=fonts["label"], fill=col)

        # Portrait canvas background
        draw.rectangle([px, py, px + PW, py + PH], fill=(8, 12, 20))
        # Faint axis cross at centre
        mid_x = PW // 2
        mid_y = PH // 2
        draw.line([px + mid_x, py + 2, px + mid_x, py + PH - 2], fill=AXIS_COL, width=1)
        draw.line([px + 2, py + mid_y, px + PW - 2, py + mid_y], fill=AXIS_COL, width=1)

        # Draw trail — scale from reference 200×200 to actual PW×PH
        # Clip all points to portrait canvas bounds
        scale_x = PW / 200.0
        scale_y = PH / 200.0
        for ti, pt in enumerate(trail_now):
            x = px + pt[0] * scale_x
            y = py + pt[1] * scale_y
            # Skip points outside portrait canvas
            if x < px - 4 or x > px + PW + 4 or y < py - 4 or y > py + PH + 4:
                continue
            frac = (ti + 1) / max(1, len(trail_now))
            alpha = frac * frac
            tc = lerp_color(col, alpha * 0.9)
            r  = max(1, round(1.5 + frac * 2.5))
            draw.ellipse([x - r, y - r, x + r, y + r], fill=tc)

        # Bright head + glow (clipped to canvas)
        if trail_now:
            pt = trail_now[-1]
            hx = px + pt[0] * scale_x
            hy = py + pt[1] * scale_y
            hx = max(px, min(px + PW, hx))
            hy = max(py, min(py + PH, hy))
            glow(draw, hx, hy, 9, col, alpha=0.28)
            draw.ellipse([hx - 4, hy - 4, hx + 4, hy + 4], fill=col)

        # Redraw portrait border to mask any glow bleed at edges
        draw.rectangle([px - 2, py - 2, px + PW + 2, py + PH + 2],
                       outline=SURFACE, width=2)
        draw.rectangle([px, py, px + PW, py + PH], outline=BORDER, width=1)

        # PC axis labels (faint, inside portrait corners)
        draw.text((px + PW - 22, py + 2), "PC2", font=fonts["axis"], fill=BORDER)
        draw.text((px + 3, py + PH - 14), "PC1", font=fonts["axis"], fill=BORDER)

        # Sub-description text below portrait
        sub_y = py + PH + 5
        sub_w = draw.textlength(regime["sub"], font=fonts["sub_small"])
        sub_x = cx + (CELL_W - int(sub_w)) // 2
        draw.text((sub_x, sub_y), regime["sub"], font=fonts["sub_small"], fill=TEXT_MED)

    return img

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Building regime GIF…")
    print(f"  Grid: {N_COLS_TOP}+{N_COLS_BOT}  Cell: {CELL_W}×{CELL_H}px  Portrait: {PORTRAIT_PS}px  Frames: {N_FRAMES}")

    random.seed(42)

    fonts = {
        "title":     load_font(28, bold=True),
        "sub":       load_font(16),
        "label":     load_font(14, bold=True),
        "footer":    load_font(13),
        "axis":      load_font(9),
        "sub_small": load_font(11),
    }

    print("  Pre-computing trails…")
    trails = build_trails(N_FRAMES, TRAIL_LEN)

    print("  Rendering frames…")
    frames = []
    for f in range(N_FRAMES):
        if f % 40 == 0:
            print(f"    Frame {f}/{N_FRAMES}")
        frames.append(render_frame(f, trails, fonts))

    print(f"  Saving → {OUT}")
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        loop=0,                  # loop forever
        duration=FRAME_MS,
        optimize=True,
    )

    size_kb = os.path.getsize(OUT) / 1024
    print(f"  Done. Size: {size_kb:.0f} KB  ({size_kb/1024:.1f} MB)")
    if size_kb > 5120:
        print("  ⚠ Warning: >5MB — LinkedIn may reject. Consider reducing N_FRAMES.")
    else:
        print("  ✓ Under 5MB — suitable for LinkedIn, Twitter, Instagram.")


if __name__ == "__main__":
    main()
