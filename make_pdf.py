#!/usr/bin/env python3
"""Render NOTES.md to a print-ready PDF via python-markdown + headless Chrome.

Usage: python3 make_pdf.py [input.md] [output.pdf]
"""
import html
import re
import os
import subprocess
import sys

import markdown

SRC = sys.argv[1] if len(sys.argv) > 1 else "NOTES.md"
OUT = sys.argv[2] if len(sys.argv) > 2 else "Beyond_Labs_ChatGPT_Retrieval_Leak_Vatsalya_Roy.pdf"
REPO = "https://github.com/Vatsalya001/beyond_labs_assignment"

CSS = """
@page { size: A4; margin: 16mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body {
  font: 10.5pt/1.5 -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #14161a; margin: 0;
}
.banner {
  border: 1px solid #d5d9e0; border-left: 4px solid #2f6feb; background: #f6f8fc;
  padding: 10px 14px; margin: 0 0 20px; border-radius: 4px; font-size: 10pt;
}
.banner a { color: #2f6feb; text-decoration: none; font-weight: 600; word-break: break-all; }
h1 { font-size: 20pt; margin: 0 0 4px; letter-spacing: -0.3px; }
h2 {
  font-size: 13.5pt; margin: 22px 0 8px; padding-bottom: 4px;
  border-bottom: 1.5px solid #e3e6ea; page-break-after: avoid;
}
h3 { font-size: 11.5pt; margin: 16px 0 6px; page-break-after: avoid; }
h1, h2, h3 { page-break-inside: avoid; }
p { margin: 7px 0; }
ul, ol { margin: 7px 0; padding-left: 20px; }
li { margin: 3px 0; }
blockquote {
  margin: 10px 0; padding: 2px 14px; border-left: 3px solid #c9cfd8;
  color: #3d434d; background: #fafbfc;
}
table {
  border-collapse: collapse; width: 100%; margin: 10px 0;
  font-size: 8.8pt; page-break-inside: avoid;
}
th, td {
  border: 1px solid #dfe3e8; padding: 5px 7px; text-align: left;
  vertical-align: top; word-break: break-word;
}
th { background: #f1f3f6; font-weight: 600; }
tr:nth-child(even) td { background: #fbfcfd; }
code {
  font-family: "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
  font-size: 8.8pt; background: #f2f4f7; padding: 1px 4px;
  border-radius: 3px; word-break: break-word;
}
pre {
  background: #f7f8fa; border: 1px solid #e3e6ea; border-radius: 4px;
  padding: 10px 12px; overflow-wrap: break-word; white-space: pre-wrap;
  font-size: 8.5pt; line-height: 1.45; page-break-inside: avoid; margin: 10px 0;
}
pre code { background: none; padding: 0; font-size: inherit; }
hr { border: none; border-top: 1px solid #e3e6ea; margin: 20px 0; }
strong { font-weight: 650; }
a { color: #2f6feb; }
"""

BANNER = f"""<div class="banner">
<strong>Code, raw capture and all extracted data:</strong><br>
<a href="{REPO}">{REPO}</a>
</div>"""


def main() -> int:
    if not os.path.exists(SRC):
        print(f"ERROR: {SRC} not found")
        return 1

    raw = open(SRC, encoding="utf-8").read()

    # python-markdown needs a blank line before a list that follows a
    # paragraph, otherwise the bullets collapse into run-on prose.
    lines, fixed, in_fence = raw.split("\n"), [], False
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and re.match(r"^\s*([-*+]|\d+\.)\s+\S", ln):
            prev = fixed[-1] if fixed else ""
            if prev.strip() and not re.match(r"^\s*([-*+]|\d+\.)\s+", prev) \
                    and not prev.lstrip().startswith(("|", ">", "#")):
                fixed.append("")
        fixed.append(ln)

    body = markdown.markdown(
        "\n".join(fixed),
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
    )
    page = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>{html.escape(os.path.splitext(OUT)[0])}</title>"
        f"<style>{CSS}</style></head><body>{BANNER}{body}</body></html>"
    )
    tmp = "/tmp/_notes_render.html"
    open(tmp, "w", encoding="utf-8").write(page)

    cmd = [
        "google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer", "--virtual-time-budget=4000",
        f"--print-to-pdf={os.path.abspath(OUT)}", f"file://{tmp}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not os.path.exists(OUT):
        print("ERROR: Chrome produced no PDF")
        print(r.stderr[-1500:])
        return 1
    print(f"OK  {OUT}  ({os.path.getsize(OUT):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
