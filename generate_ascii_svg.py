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
        text_color = "#c9d1d9"
        key_color = "#ffa657"
        value_color = "#a5d6ff"
        add_color = "#3fb950"
        del_color = "#f85149"
        cc_color = "#616e7f"
    else:
        # light mode
        bg_color = "#ffffff"
        text_color = "#24292f"
        key_color = "#953800"
        value_color = "#0a3069"
        add_color = "#1a7f37"
        del_color = "#cf222e"
        cc_color = "#57606a"

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="985px" height="530px" font-size="16px">
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
<rect width="985px" height="530px" fill="{bg_color}" rx="15"/>
<image x="15" y="15" width="360" height="500" preserveAspectRatio="xMidYMid meet" href="{image_uri}"/>
<text x="390" y="30" fill="{text_color}">
<tspan x="390" y="30">satya@github</tspan> ─────────────────────────────────────
<tspan x="390" y="50">  <tspan class="key">Name</tspan> ......... <tspan class="value">Satya Sarthak Manohari</tspan></tspan>
<tspan x="390" y="70">  <tspan class="key">Role</tspan> ......... <tspan class="value">Cybersecurity | Backend Engineer</tspan></tspan>
<tspan x="390" y="90">  <tspan class="key">Location</tspan> ..... <tspan class="value">Odisha, India</tspan></tspan>
<tspan x="390" y="110">  <tspan class="key">Age</tspan> .......... <tspan class="value" id="age_data">—</tspan></tspan>
<tspan x="390" y="130">  <tspan class="key">Uptime</tspan> ....... <tspan class="value" id="uptime_data">—</tspan></tspan>
<tspan x="390" y="150">  <tspan class="key">Education</tspan> .... <tspan class="value">B.Tech CSE (Cybersecurity) at SSU</tspan></tspan>
<tspan x="390" y="170">  <tspan class="key">Internship</tspan> ... <tspan class="value">NISER, Soilveda, CyberDojo</tspan></tspan>
<tspan x="390" y="190">  <tspan class="key">Work</tspan> ......... <tspan class="value">Backend Engineer</tspan></tspan>
<tspan x="390" y="210">  <tspan class="key">Goal</tspan> ......... <tspan class="value">"Build secure, resilient systems."</tspan></tspan>
<tspan x="390" y="230"></tspan>
<tspan x="390" y="250">─ Tech Stack ───────────────────────────────────────</tspan>
<tspan x="390" y="270">  <tspan class="key">Languages</tspan> .... <tspan class="value">C, C++, Java, Python</tspan></tspan>
<tspan x="390" y="290">  <tspan class="key">Backend</tspan> ...... <tspan class="value">Flask, Django, FastAPI</tspan></tspan>
<tspan x="390" y="310">  <tspan class="key">Database</tspan> ..... <tspan class="value">PostgreSQL, MySQL, MongoDB</tspan></tspan>
<tspan x="390" y="330">  <tspan class="key">Cloud/DevOps</tspan> . <tspan class="value">AWS (Certified Cloud Practitioner), Docker</tspan></tspan>
<tspan x="390" y="350">  <tspan class="key">Security</tspan> ..... <tspan class="value">Kali Linux, Wireshark, SIEM</tspan></tspan>
<tspan x="390" y="370"></tspan>
<tspan x="390" y="390">─ Current Focus ────────────────────────────────────</tspan>
<tspan x="390" y="410">  <tspan class="key">Target</tspan> ....... <tspan class="value">GATE CSE 2027 &amp; 2028</tspan></tspan>
<tspan x="390" y="430">  <tspan class="key">Focus</tspan> ........ <tspan class="value">DSA &amp; Secure Backend Systems</tspan></tspan>
<tspan x="390" y="450">─ GitHub Stats ─────────────────────────────────────</tspan>
<tspan x="390" y="470">  <tspan class="key">Repos</tspan>:<tspan class="cc" id="repo_data_dots"> .... </tspan><tspan class="value" id="repo_data">—</tspan> {{<tspan class="key">Contributed</tspan>: <tspan class="value" id="contrib_data">—</tspan>}} | <tspan class="key">Stars</tspan>:<tspan class="cc" id="star_data_dots"> ........... </tspan><tspan class="value" id="star_data">—</tspan></tspan>
<tspan x="390" y="490">  <tspan class="key">Commits</tspan>:<tspan class="cc" id="commit_data_dots"> ................... </tspan><tspan class="value" id="commit_data">—</tspan> | <tspan class="key">Followers</tspan>:<tspan class="cc" id="follower_data_dots"> ....... </tspan><tspan class="value" id="follower_data">—</tspan></tspan>
<tspan x="390" y="510">  <tspan class="key">Lines of Code on GitHub</tspan>:<tspan class="cc" id="loc_data_dots">. </tspan><tspan class="value" id="loc_data">—</tspan> ( <tspan class="addColor" id="loc_add">0</tspan><tspan class="addColor">++</tspan>, <tspan id="loc_del_dots"> </tspan><tspan class="delColor" id="loc_del">0</tspan><tspan class="delColor">--</tspan> )</tspan>
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
