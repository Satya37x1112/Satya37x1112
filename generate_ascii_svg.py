"""
generate_ascii_svg.py — Generates neofetch-style dark_mode.svg and light_mode.svg
dashboards by directly embedding ascii-art.png on the left, and a structured
GitHub stats panel on the right.
"""

import base64
import os
import sys

# ─── Configuration ────────────────────────────────────────────────────────────

ASCII_ART_IMAGE = "ascii-art.png"

# ─── Image Encoder ────────────────────────────────────────────────────────────

def encode_image_base64(filepath):
    """Loads a file and returns its base64 data URI."""
    if not os.path.exists(filepath):
        print(f"  ❌ {filepath} not found. Aborting.")
        sys.exit(1)
    with open(filepath, "rb") as f:
        binary_data = f.read()
        base_64 = base64.b64encode(binary_data).decode("utf-8")
        return f"data:image/png;base64,{base_64}"

# ─── SVG Generator ────────────────────────────────────────────────────────────

def generate_svg(theme_name, image_uri):
    """Creates the complete SVG string based on the theme and embedded image URI."""
    if theme_name == "dark":
        bg_color = "#161b22"
        stroke_color = "#30363d"
        text_color = "#c9d1d9"
        key_color = "#ffa657"
        value_color = "#a5d6ff"
        add_color = "#3fb950"
        del_color = "#f85149"
        cc_color = "#616e7f"
    else:
        # light mode
        bg_color = "#ffffff"
        stroke_color = "#d0d7de"
        text_color = "#24292f"
        key_color = "#953800"
        value_color = "#0a3069"
        add_color = "#1a7f37"
        del_color = "#cf222e"
        cc_color = "#57606a"

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="985px" height="580px" font-size="16px">
<defs>
  <clipPath id="image-clip">
    <rect x="20" y="20" width="360" height="540" rx="12" ry="12" />
  </clipPath>
</defs>
<style>
@font-face {{
  src: local('Consolas'), local('Consolas Bold');
  font-family: 'ConsolasFallback';
  font-display: swap;
  -webkit-size-adjust: 109%;
  size-adjust: 109%;
}}
.key {{fill: {key_color};}}
.value {{fill: {value_color};}}
.addColor {{fill: {add_color};}}
.delColor {{fill: {del_color};}}
.cc {{fill: {cc_color};}}
text, tspan {{white-space: pre;}}
</style>
<rect x="1" y="1" width="983px" height="578px" fill="{bg_color}" stroke="{stroke_color}" stroke-width="1.5" rx="20"/>
<image x="20" y="20" width="360" height="540" clip-path="url(#image-clip)" preserveAspectRatio="xMidYMid meet" href="{image_uri}"/>
<text x="410" y="45" fill="{text_color}">
<tspan x="410" y="45" font-weight="bold"><tspan class="key">satya</tspan>@<tspan class="value">github</tspan></tspan>
<tspan x="410" y="57" class="cc">────────────</tspan>
<tspan x="410" y="80">  <tspan class="key">Name</tspan>          : <tspan class="value">Satya Sarthak Manohari</tspan></tspan>
<tspan x="410" y="100">  <tspan class="key">Role</tspan>          : <tspan class="value">Cybersecurity | Backend Engineer</tspan></tspan>
<tspan x="410" y="120">  <tspan class="key">Location</tspan>      : <tspan class="value">Odisha, India</tspan></tspan>
<tspan x="410" y="140">  <tspan class="key">Age</tspan>           : <tspan class="value" id="age_data">—</tspan></tspan>
<tspan x="410" y="160">  <tspan class="key">Uptime</tspan>        : <tspan class="value" id="uptime_data">—</tspan></tspan>
<tspan x="410" y="180">  <tspan class="key">Education</tspan>     : <tspan class="value">B.Tech CSE (Cybersecurity) at SSU</tspan></tspan>
<tspan x="410" y="200">  <tspan class="key">Internship</tspan>    : <tspan class="value">NISER, Soilveda, CyberDojo</tspan></tspan>
<tspan x="410" y="220">  <tspan class="key">Work</tspan>          : <tspan class="value">Backend Engineer</tspan></tspan>
<tspan x="410" y="240">  <tspan class="key">Goal</tspan>          : <tspan class="value">"Build secure, resilient systems."</tspan></tspan>
<tspan x="410" y="270" class="cc">─ Tech Stack ───────────────────────────────────────</tspan>
<tspan x="410" y="295">  <tspan class="key">Languages</tspan>     : <tspan class="value">C, C++, Java, Python</tspan></tspan>
<tspan x="410" y="315">  <tspan class="key">Backend</tspan>       : <tspan class="value">Flask, Django, FastAPI</tspan></tspan>
<tspan x="410" y="335">  <tspan class="key">Database</tspan>      : <tspan class="value">PostgreSQL, MySQL, MongoDB</tspan></tspan>
<tspan x="410" y="355">  <tspan class="key">Cloud/DevOps</tspan>  : <tspan class="value">AWS (Certified Cloud Practitioner), Docker</tspan></tspan>
<tspan x="410" y="375">  <tspan class="key">Security</tspan>      : <tspan class="value">Kali Linux, Wireshark, SIEM</tspan></tspan>
<tspan x="410" y="405" class="cc">─ Current Focus ────────────────────────────────────</tspan>
<tspan x="410" y="430">  <tspan class="key">Target</tspan>        : <tspan class="value">GATE CSE 2027 &amp; 2028</tspan></tspan>
<tspan x="410" y="450">  <tspan class="key">Focus</tspan>         : <tspan class="value">DSA &amp; Secure Backend Systems</tspan></tspan>
<tspan x="410" y="480" class="cc">─ GitHub Stats ─────────────────────────────────────</tspan>
<tspan x="410" y="505">  <tspan class="key">Repos</tspan>         : <tspan class="value" id="repo_data">—</tspan> (<tspan class="value" id="contrib_data">—</tspan> contributed)</tspan><tspan x="785">| <tspan class="key">Stars</tspan>     : <tspan class="value" id="star_data">—</tspan></tspan>
<tspan x="410" y="525">  <tspan class="key">Commits</tspan>       : <tspan class="value" id="commit_data">—</tspan></tspan><tspan x="785">| <tspan class="key">Followers</tspan> : <tspan class="value" id="follower_data">—</tspan></tspan>
<tspan x="410" y="545">  <tspan class="key">Lines of Code</tspan> : <tspan class="value" id="loc_data">—</tspan> ( <tspan class="addColor" id="loc_add">0</tspan><tspan class="addColor">++</tspan>, <tspan class="delColor" id="loc_del">0</tspan><tspan class="delColor">--</tspan> )</tspan>
</text>
</svg>
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"Encoding {ASCII_ART_IMAGE} to base64...")
    image_uri = encode_image_base64(ASCII_ART_IMAGE)
    print(f"  ✅ Encoded ({len(image_uri)} characters).")

    print("Generating SVGs...")
    dark_svg = generate_svg("dark", image_uri)
    light_svg = generate_svg("light", image_uri)

    with open("dark_mode.svg", "w", encoding="utf-8") as f:
        f.write(dark_svg)
    print("  ✅ Wrote dark_mode.svg")

    with open("light_mode.svg", "w", encoding="utf-8") as f:
        f.write(light_svg)
    print("  ✅ Wrote light_mode.svg")


if __name__ == "__main__":
    main()
