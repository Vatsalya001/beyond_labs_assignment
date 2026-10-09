#!/usr/bin/env python3
"""Recursively inventory a captured AI-assistant response stream.

Makes ZERO assumptions about field names. That is the whole point: these are
undocumented private APIs whose key names drift, so step one is to discover
what is actually in *your* payload rather than trust anyone's field list.

Reports:
  * how many frames parsed, and how many look like JSON-patch deltas
    (this tells you whether a reassembly pass is required)
  * top-level frame shapes
  * type discriminators (type / content_type / recipient / role / op ...)
  * the biggest arrays        -> candidates for the retrieval set
  * every interesting key path
  * every distinct URL + where it was found
  * every long string         -> snippets, descriptions, answer text

Usage:
    python3 parse/inventory.py capture/chatgpt_raw.txt | tee out/key_inventory.txt
"""

from __future__ import annotations

import collections
import json
import re
import sys

URL_RE = re.compile(r"https?://[^\s\"'<>)\]\\]+")

INTERESTING = re.compile(
    r"url|title|snippet|quer|cite|source|ref|search|text|desc|channel|view|like|"
    r"follow|verif|date|time|video|attribution|type|recipient|rank|score|author|"
    r"domain|site|name|thumb|result|group|entr",
    re.I,
)

DISCRIMINATOR_KEYS = {
    "type", "content_type", "recipient", "role", "o", "op", "name", "status",
    "source_type", "kind", "event", "command", "model_slug", "finish_type",
}

# A frame is "patch-like" if its key set is small and looks like path/op/value.
PATCHY_KEYSETS = [
    {"p", "o", "v"}, {"p", "v"}, {"o", "v"}, {"v"},
    {"p", "o", "v", "c"}, {"v", "c"},
    {"path", "op", "value"}, {"op", "value"},
]


def frames(text: str):
    """Yield (line_no, parsed_json) for every JSON value recoverable from the dump.

    Handles: SSE 'data:' lines, bare NDJSON lines, and the '===== #01 ... ====='
    separators written by interceptor.js. Skips 'event:' lines, comments and
    the [DONE] sentinel.
    """
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith(("event:", "id:", "retry:", ":", "=====")):
            continue
        if s.startswith("data:"):
            s = s[5:].strip()
        if not s or s in ("[DONE]", '"[DONE]"'):
            continue
        try:
            yield i, json.loads(s)
        except json.JSONDecodeError:
            # Try to salvage an embedded object (some transports prefix junk).
            brace = s.find("{")
            if brace > 0:
                try:
                    yield i, json.loads(s[brace:])
                except json.JSONDecodeError:
                    pass


def is_patchy(obj) -> bool:
    return isinstance(obj, dict) and set(obj) in PATCHY_KEYSETS


def walk(node, path, keys, urls, arrays, strings, discriminators):
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}"
            keys[p] += 1
            if k.lower() in DISCRIMINATOR_KEYS and isinstance(v, (str, int, bool)):
                sv = str(v)
                if len(sv) < 60:
                    discriminators[k][sv] += 1
            walk(v, p, keys, urls, arrays, strings, discriminators)
    elif isinstance(node, list):
        if len(node) >= 3:
            arrays[path] = max(arrays.get(path, 0), len(node))
        for v in node:
            walk(v, f"{path}[]", keys, urls, arrays, strings, discriminators)
    elif isinstance(node, str):
        for u in URL_RE.findall(node):
            urls[u].add(path)
        if len(node) > 400:
            strings.append((len(node), path, node[:140].replace("\n", " ⏎ ")))


def main() -> int:
    raw_path = sys.argv[1] if len(sys.argv) > 1 else "capture/chatgpt_raw.txt"
    try:
        text = open(raw_path, encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        print(f"ERROR: {raw_path} not found. Capture the stream first (Phase 1).")
        return 1

    keys: collections.Counter = collections.Counter()
    urls: dict = collections.defaultdict(set)
    arrays: dict = {}
    strings: list = []
    discriminators: dict = collections.defaultdict(collections.Counter)
    shapes: collections.Counter = collections.Counter()

    total = patchy = 0
    for _, obj in frames(text):
        total += 1
        if is_patchy(obj):
            patchy += 1
        if isinstance(obj, dict):
            shapes[tuple(sorted(obj.keys())[:8])] += 1
        else:
            shapes[(f"<{type(obj).__name__}>",)] += 1
        walk(obj, "$", keys, urls, arrays, strings, discriminators)

    w = sys.stdout.write

    w(f"FILE               : {raw_path}\n")
    w(f"RAW CHARS          : {len(text):,}\n")
    w(f"PARSEABLE FRAMES   : {total:,}\n")
    if total:
        w(f"PATCH-LIKE FRAMES  : {patchy:,}  ({patchy / total * 100:.0f}% of frames)\n")
        if patchy > total * 0.2:
            w(
                "\n  >>> HIGH patch-frame count. The stream mixes full objects with\n"
                "      JSON-patch-style deltas that mutate objects sent earlier.\n"
                "      A line-by-line parser WILL silently drop patch-only content.\n"
                "      Use the reassembly pass in parse_chatgpt.py.\n"
            )
        else:
            w(
                "\n  >>> LOW patch-frame count. The stream looks mostly like full\n"
                "      objects. Reassembly may be unnecessary — confirm below.\n"
            )
    if not total:
        w(
            "\n  >>> ZERO frames parsed. Either the capture is empty, or the\n"
            "      transport is not SSE/NDJSON JSON. Inspect the head of the file:\n"
            f"        head -c 2000 {raw_path}\n"
        )

    w("\n=== FRAME SHAPES (top-level key sets; tiny sets are the delta frames) ===\n")
    for shape, c in shapes.most_common(25):
        w(f"{c:7,d}  {list(shape)}\n")

    w("\n=== TYPE DISCRIMINATORS (these tell you which frames to target) ===\n")
    if not discriminators:
        w("  (none found)\n")
    for k in sorted(discriminators):
        w(f"\n  {k}:\n")
        for v, c in discriminators[k].most_common(30):
            w(f"    {c:7,d}  {v}\n")

    w("\n=== BIGGEST ARRAYS (candidates for the retrieval set) ===\n")
    for path, n in sorted(arrays.items(), key=lambda kv: -kv[1])[:30]:
        w(f"{n:7,d}  {path}\n")

    w("\n=== INTERESTING KEY PATHS ===\n")
    shown = 0
    for path, c in keys.most_common():
        if INTERESTING.search(path.rsplit(".", 1)[-1]):
            w(f"{c:7,d}  {path}\n")
            shown += 1
    if not shown:
        w("  (none matched — widen the INTERESTING regex, or the payload is positional)\n")

    w(f"\n=== DISTINCT URLS ({len(urls)}) ===\n")
    for u in sorted(urls):
        w(f"  {u}\n       at: {sorted(urls[u])[:3]}\n")

    yt = [u for u in urls if re.search(r"youtube\.com|youtu\.be", u)]
    w(f"\n=== YOUTUBE URLS ({len(yt)}) ===\n")
    for u in yt:
        w(f"  {u}\n")
    if not yt:
        w("  (none — consider the backup prompt, see APPROACH.md §0)\n")

    w("\n=== LONG STRINGS >400 chars (snippets / descriptions / answer text) ===\n")
    for n, path, head in sorted(strings, reverse=True)[:25]:
        w(f"{n:7,d}  {path}\n         {head}\n")
    if not strings:
        w("  (none)\n")

    w("\n=== TRANSCRIPT-SHAPED KEYS (expected: none) ===\n")
    hits = sorted({m.group(0) for m in re.finditer(
        r'"[a-z_]*(?:transcript|caption|subtitle|srt|vtt)[a-z_]*"', text, re.I)})
    w(("  " + "\n  ".join(hits)) if hits else
      "  none — ChatGPT did not receive a transcript. This absence IS the finding.\n")
    w("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
