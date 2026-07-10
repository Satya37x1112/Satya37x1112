"""
generate_ascii_svg.py — Generates dark_mode.svg and light_mode.svg dashboards
with true-color ASCII art from the `ascii-view` C engine.

Pipeline:
  1. `ascii-view` converts prof0_original.png → ANSI truecolor text (temp_ascii_svg.txt)
  2. This script parses the ANSI escape codes to extract per-character (char, r, g, b)
  3. Builds SVG files with <tspan> elements for each colored character
  4. Stats panel with element IDs is placed on the right side
  5. update_stats.py then writes live GitHub stats into those element IDs

Usage:
    # Compile ascii-view first (if not already built):
    make release

    # Generate the ASCII text:
    ./ascii-view prof0_original.png -mw 80 -mh 40 > temp_ascii_svg.txt

    # Build SVGs:
    python3 generate_ascii_svg.py
"""

import colorsys
import os
import re
import subprocess
import sys

from lxml import etree

# ─── Configuration ────────────────────────────────────────────────────────────

# Dimensions for ASCII art (passed to ascii-view)
ASCII_WIDTH = 80
ASCII_HEIGHT = 40

# Source image for ascii-view
SOURCE_IMAGE = "prof0_original.png"

# Intermediate ANSI text file
ASCII_TEXT_FILE = "temp_ascii_svg.txt"

# ASCII-view binary
ASCII_VIEW_BIN = "./ascii-view"

# SVG layout parameters
SVG_WIDTH = 880
SVG_HEIGHT = 360
ASCII_X = 18          # Left margin for ASCII art
ASCII_Y = 48          # Top of ASCII art
CHAR_WIDTH = 4.85     # Width per character in SVG (monospace at 7px)
LINE_HEIGHT = 7.8     # Vertical spacing between ASCII rows
FONT_SIZE_ASCII = 7
FONT_SIZE_LABEL = 11.5
FONT_SIZE_TITLE = 14
STATS_X = 440         # Stats panel left edge

# XML namespace
SVG_NS = "http://www.w3.org/2000/svg"
XML_NS = "http://www.w3.org/XML/1998/namespace"


# ─── ANSI Parser ─────────────────────────────────────────────────────────────

# Matches: \x1b[38;2;R;G;Bm<char>  or  \x1b[0m (reset)
ANSI_PATTERN = re.compile(r'\x1b\[38;2;(\d+);(\d+);(\d+)m(.)')
ANSI_RESET = re.compile(r'\x1b\[0m')


def parse_ansi_file(filepath):
    """
    Parses a file containing ANSI 24-bit truecolor escape codes.
    Returns a list of rows, where each row is a list of (char, r, g, b) tuples.
    """
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            row = []
            pos = 0
            while pos < len(line):
                # Try matching a colored character
                match = ANSI_PATTERN.match(line, pos)
                if match:
                    r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    char = match.group(4)
                    row.append((char, r, g, b))
                    pos = match.end()
                    continue

                # Try matching reset code
                reset = ANSI_RESET.match(line, pos)
                if reset:
                    pos = reset.end()
                    continue

                # Plain character (no escape code)
                ch = line[pos]
                if ch not in ("\n", "\r"):
                    row.append((ch, 200, 200, 200))
                pos += 1

            if row:
                rows.append(row)
    return rows


# ─── SVG Builder ─────────────────────────────────────────────────────────────


def adapt_color_for_light_mode(r, g, b):
    """
    Converts a color designed for dark backgrounds into one that looks
    vivid on a white background.

    Strategy: convert to HSV, boost saturation slightly, and clamp
    value (brightness) to ≤0.35 so characters stay dark and readable
    on white while preserving their hue.
    """
    # Normalize to 0-1 range
    rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(rn, gn, bn)

    # Boost saturation for vividness on white
    s = min(1.0, s * 1.3)

    # Clamp brightness low — dark characters on white background
    v = min(0.35, v * 0.4)

    rn, gn, bn = colorsys.hsv_to_rgb(h, s, v)
    return int(rn * 255), int(gn * 255), int(bn * 255)


def _color_str(r, g, b):
    """Returns an SVG-compatible rgb() color string."""
    return f"rgb({r},{g},{b})"


def build_svg(output_path, ascii_rows, theme="dark"):
    """
    Builds a complete SVG with true-color ASCII art portrait (left)
    and stats panel (right).
    """
    # ── Theme colors ──────────────────────────────────────────────────────
    themes = {
        "dark": {
            "bg": "#0d1117", "text": "#c9d1d9", "label": "#8b949e",
            "title": "#58a6ff", "dots": "#30363d", "border": "#21262d",
            "add": "#3fb950", "del": "#f85149", "accent": "#1f6feb",
        },
        "light": {
            "bg": "#ffffff", "text": "#24292f", "label": "#57606a",
            "title": "#0969da", "dots": "#d0d7de", "border": "#d0d7de",
            "add": "#1a7f37", "del": "#cf222e", "accent": "#0969da",
        },
    }
    c = themes[theme]

    # ── Build SVG root ────────────────────────────────────────────────────
    nsmap = {None: SVG_NS}
    root = etree.Element("svg", nsmap=nsmap)
    root.set("width", str(SVG_WIDTH))
    root.set("height", str(SVG_HEIGHT))
    root.set("viewBox", f"0 0 {SVG_WIDTH} {SVG_HEIGHT}")

    # Stylesheet
    defs = etree.SubElement(root, "defs")
    style = etree.SubElement(defs, "style")
    style.text = f"""
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');
      .bg {{ fill: {c['bg']}; }}
      .title {{ font-family: 'JetBrains Mono', monospace; font-size: {FONT_SIZE_TITLE}px; font-weight: 600; fill: {c['title']}; }}
      .label {{ font-family: 'JetBrains Mono', monospace; font-size: {FONT_SIZE_LABEL}px; fill: {c['label']}; }}
      .value {{ font-family: 'JetBrains Mono', monospace; font-size: {FONT_SIZE_LABEL}px; fill: {c['text']}; }}
      .dots  {{ font-family: 'JetBrains Mono', monospace; font-size: {FONT_SIZE_LABEL}px; fill: {c['dots']}; }}
      .ascii {{ font-family: 'JetBrains Mono', monospace; font-size: {FONT_SIZE_ASCII}px; }}
      .add   {{ fill: {c['add']}; }}
      .del   {{ fill: {c['del']}; }}
      .border {{ fill: none; stroke: {c['border']}; stroke-width: 1; rx: 12; ry: 12; }}
      .divider {{ stroke: {c['border']}; stroke-width: 1; }}
      .accent-line {{ stroke: {c['accent']}; stroke-width: 2; }}
    """

    # Background + border
    for cls in ("bg", "border"):
        rect = etree.SubElement(root, "rect")
        rect.set("class", cls)
        rect.set("x", "0.5")
        rect.set("y", "0.5")
        rect.set("width", str(SVG_WIDTH - 1))
        rect.set("height", str(SVG_HEIGHT - 1))
        rect.set("rx", "12")
        rect.set("ry", "12")

    # Title
    title = etree.SubElement(root, "text")
    title.set("class", "title")
    title.set("x", str(ASCII_X))
    title.set("y", "28")
    title.text = "Satya37x1112"

    subtitle = etree.SubElement(root, "text")
    subtitle.set("class", "label")
    subtitle.set("x", str(ASCII_X + 130))
    subtitle.set("y", "28")
    subtitle.text = "· GitHub Stats Dashboard"

    # Accent line under title
    line_el = etree.SubElement(root, "line")
    line_el.set("class", "accent-line")
    line_el.set("x1", str(ASCII_X))
    line_el.set("y1", "35")
    line_el.set("x2", str(SVG_WIDTH - 20))
    line_el.set("y2", "35")

    # ── ASCII Art (left side) — true-color per character ──────────────────
    for row_idx, row in enumerate(ascii_rows):
        y_pos = ASCII_Y + row_idx * LINE_HEIGHT

        # Create a parent <text> element for this row
        text_el = etree.SubElement(root, "text")
        text_el.set("class", "ascii")
        text_el.set("x", str(ASCII_X))
        text_el.set("y", f"{y_pos:.1f}")
        text_el.set(f"{{{XML_NS}}}space", "preserve")

        # Group consecutive characters with the same color into single tspans
        # to reduce SVG size dramatically
        groups = []
        current_chars = ""
        current_color = None
        for char, r, g, b in row:
            color = (r, g, b)
            if color == current_color:
                current_chars += char
            else:
                if current_chars:
                    groups.append((current_chars, current_color))
                current_chars = char
                current_color = color
        if current_chars:
            groups.append((current_chars, current_color))

        # First group goes as direct text, rest as tspans
        if groups:
            first_chars, first_color = groups[0]
            fc = adapt_color_for_light_mode(*first_color) if theme == "light" else first_color
            text_el.set("fill", _color_str(*fc))
            text_el.text = first_chars

            for chars, color in groups[1:]:
                tspan = etree.SubElement(text_el, "tspan")
                tc = adapt_color_for_light_mode(*color) if theme == "light" else color
                tspan.set("fill", _color_str(*tc))
                tspan.text = chars

    # ── Vertical divider ──────────────────────────────────────────────────
    divider = etree.SubElement(root, "line")
    divider.set("class", "divider")
    divider.set("x1", str(STATS_X - 15))
    divider.set("y1", "42")
    divider.set("x2", str(STATS_X - 15))
    divider.set("y2", str(SVG_HEIGHT - 20))

    # ── Stats Panel (right side) ──────────────────────────────────────────
    stats_y_start = 68
    stat_row_height = 28

    stats = [
        ("Commits", "commit_data", 22),
        ("Stars", "star_data", 14),
        ("Repositories", "repo_data", 6),
        ("Contributed To", "contrib_data", 0),
        ("Followers", "follower_data", 10),
        ("Lines of Code", "loc_data", 9),
    ]

    for idx, (label_text, element_id, dot_len) in enumerate(stats):
        y_pos = stats_y_start + idx * stat_row_height

        label_el = etree.SubElement(root, "text")
        label_el.set("class", "label")
        label_el.set("x", str(STATS_X))
        label_el.set("y", str(y_pos))
        label_el.text = label_text

        dots_el = etree.SubElement(root, "text")
        dots_el.set("class", "dots")
        dots_el.set("id", f"{element_id}_dots")
        dots_el.set("x", str(STATS_X + 150))
        dots_el.set("y", str(y_pos))
        dots_el.text = "." * dot_len if dot_len > 0 else ""

        value_el = etree.SubElement(root, "text")
        value_el.set("class", "value")
        value_el.set("id", element_id)
        value_el.set("x", str(STATS_X + 310))
        value_el.set("y", str(y_pos))
        value_el.text = "—"

    # ── LOC Added / Deleted ───────────────────────────────────────────────
    loc_y = stats_y_start + len(stats) * stat_row_height + 14

    sep = etree.SubElement(root, "line")
    sep.set("class", "divider")
    sep.set("x1", str(STATS_X))
    sep.set("y1", str(loc_y - 16))
    sep.set("x2", str(SVG_WIDTH - 20))
    sep.set("y2", str(loc_y - 16))

    # Added
    for label, eid, cls, x_label, x_dots, x_val, dots in [
        ("Added", "loc_add", "add", STATS_X, STATS_X + 60, STATS_X + 110, ""),
        ("Deleted", "loc_del", "del", STATS_X + 210, STATS_X + 280, STATS_X + 350, "." * 7),
    ]:
        lbl = etree.SubElement(root, "text")
        lbl.set("class", "label")
        lbl.set("x", str(x_label))
        lbl.set("y", str(loc_y))
        lbl.text = label

        d = etree.SubElement(root, "text")
        d.set("class", "dots")
        d.set("id", f"{eid}_dots")
        d.set("x", str(x_dots))
        d.set("y", str(loc_y))
        d.text = dots

        v = etree.SubElement(root, "text")
        v.set("class", f"value {cls}")
        v.set("id", eid)
        v.set("x", str(x_val))
        v.set("y", str(loc_y))
        v.text = "++0" if cls == "add" else "--0"

    # ── Write SVG ─────────────────────────────────────────────────────────
    tree = etree.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True, pretty_print=True)
    print(f"  ✅ Generated {output_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    # Step 1: Generate ANSI truecolor ASCII art via the C engine
    if os.path.exists(ASCII_VIEW_BIN) and os.path.exists(SOURCE_IMAGE):
        print(f"Running ascii-view: {SOURCE_IMAGE} → {ASCII_TEXT_FILE}")
        result = subprocess.run(
            [ASCII_VIEW_BIN, SOURCE_IMAGE, "-mw", str(ASCII_WIDTH), "-mh", str(ASCII_HEIGHT)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            with open(ASCII_TEXT_FILE, "w") as f:
                f.write(result.stdout)
            print(f"  ✅ Generated {ASCII_TEXT_FILE} ({len(result.stdout)} bytes)")
        else:
            print(f"  ⚠️  ascii-view failed: {result.stderr}")
            if not os.path.exists(ASCII_TEXT_FILE):
                print("  ❌ No fallback ASCII text file found. Aborting.")
                sys.exit(1)
            print(f"  Using existing {ASCII_TEXT_FILE}")
    elif not os.path.exists(ASCII_TEXT_FILE):
        print(f"  ❌ Neither {ASCII_VIEW_BIN} nor {ASCII_TEXT_FILE} found. Aborting.")
        sys.exit(1)
    else:
        print(f"  Using existing {ASCII_TEXT_FILE}")

    # Step 2: Parse the ANSI output
    print(f"Parsing ANSI truecolor data from {ASCII_TEXT_FILE}...")
    ascii_rows = parse_ansi_file(ASCII_TEXT_FILE)
    print(f"  Parsed {len(ascii_rows)} rows, max {max(len(r) for r in ascii_rows)} cols")

    # Step 3: Build both SVGs
    print("Building SVG dashboards...")
    build_svg("dark_mode.svg", ascii_rows, theme="dark")
    build_svg("light_mode.svg", ascii_rows, theme="light")

    print("\nDone! Both SVG dashboards generated with true-color ASCII art.")


if __name__ == "__main__":
    main()
