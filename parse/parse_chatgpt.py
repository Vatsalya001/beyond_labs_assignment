#!/usr/bin/env python3
"""Extract citation snapshots + fan-out queries from a captured ChatGPT stream.

Task 1 -> out/citations.json, out/citations.csv, out/youtube_snapshot.json
Task 2 -> out/fanout_queries.json, out/retrieved_vs_cited.md

Written against a real capture (chatgpt.com/backend-api/f/conversation, gpt-6,
free account, Oct 2026). Three properties of that stream drive the design:

1. HYBRID FRAMING. The stream mixes full objects with JSON-patch deltas
   ({"c":N,"o":"append","p":"/message/content/parts/0","v":"..."}). Patches
   mutate a message announced in an EARLIER frame, so reassembly is stateful:
   you must track the currently-streaming message and apply pointers to it.
   A line-by-line parser silently drops every patch-only field.

2. DELTAS ARE MIRRORED. Each content delta appears TWICE — once live, once
   through a revision/streaming_parent_patch channel. Without dedupe the
   reassembled answer is exactly doubled.

3. CITATIONS ARE NOT INLINE MARKERS. There is no "citeturn0search3" text in
   the answer. Citations are `type: "cite"` objects carrying safe_urls[] plus
   entities[].ref strings like "turn828649search4", which resolve against
   search_result entries' ref_id {turn_index, ref_type, ref_index}.

Field names here were DISCOVERED from the payload via inventory.py, not
assumed. Re-run inventory.py on any new capture before trusting them.

Usage:
    python3 parse/parse_chatgpt.py [capture/chatgpt_raw.txt] [out]
"""

from __future__ import annotations

import collections
import copy
import csv
import json
import os
import re
import sys

YT_RE = re.compile(r"youtube\.com|youtu\.be", re.I)
REF_RE = re.compile(r"turn(\d+)([a-z]+)(\d+)", re.I)
# NOTE: deliberately excludes "subtitle" — in this payload that matches an
# advertising card's {"title": ..., "subtitle": "Sponsored"}, not a video
# caption track. Including it produced a false positive on the headline claim.
TRANSCRIPT_RE = re.compile(
    r'"[a-z_]*(?:transcript|closed_caption|captions?|srt|vtt)[a-z_]*"', re.I)
# YouTube attributes the "ChatGPT Retrieval Leak" writeup claims are present.
YT_CLAIMED_FIELDS = [
    "channel", "channel_name", "followers", "follower_count", "subscribers",
    "subscriber_count", "verified", "is_verified", "views", "view_count",
    "likes", "like_count", "description", "transcript",
]


# ── frame parsing ───────────────────────────────────────────────────────────
def frames(text: str):
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("event:", "id:", "retry:", ":", "=====")):
            continue
        if s.startswith("data:"):
            s = s[5:].strip()
        if not s or s in ("[DONE]", '"[DONE]"'):
            continue
        try:
            yield json.loads(s)
        except json.JSONDecodeError:
            brace = s.find("{")
            if brace > 0:
                try:
                    yield json.loads(s[brace:])
                except json.JSONDecodeError:
                    pass


# ── stateful JSON-pointer reassembly ────────────────────────────────────────
def ptr_apply(root, path, op, val):
    toks = [t.replace("~1", "/").replace("~0", "~")
            for t in path.split("/") if t != ""]
    if not toks:
        return
    parent = root
    for tok in toks[:-1]:
        if isinstance(parent, list):
            parent = parent[int(tok)]
        else:
            if tok not in parent or not isinstance(parent[tok], (dict, list)):
                parent[tok] = {}
            parent = parent[tok]
    last = toks[-1]
    if isinstance(parent, list):
        i = int(last)
        while len(parent) <= i:
            parent.append("")
        if op == "append" and isinstance(parent[i], str) and isinstance(val, str):
            parent[i] += val
        else:
            parent[i] = val
        return
    cur = parent.get(last)
    if op == "append":
        if isinstance(cur, str) and isinstance(val, str):
            parent[last] = cur + val
        elif isinstance(cur, list) and isinstance(val, list):
            cur.extend(val)
        else:
            parent[last] = val
    elif op == "remove":
        parent.pop(last, None)
    else:  # replace / add
        parent[last] = val


class Reassembler:
    """Rebuilds message objects from the hybrid full-object + patch stream."""

    def __init__(self):
        self.messages = []
        self.current = None
        self.last_append = {}   # path -> last value appended (mirror dedupe)
        self.dupes_skipped = 0
        self.patches = 0

    def feed(self, obj):
        if not isinstance(obj, dict):
            return
        v, p, op = obj.get("v"), obj.get("p"), obj.get("o")

        if isinstance(v, dict) and "message" in v:
            self.current = copy.deepcopy(v)
            self.messages.append(self.current)
            self.last_append.clear()
            return

        if isinstance(v, list) and op in (None, "patch"):
            for sub in v:
                self.feed(sub)
            return

        if p is not None and self.current is not None:
            self._apply(p, op or "replace", v)
            return

        if p is None and isinstance(v, str) and self.current is not None:
            self._apply("/message/content/parts/0", "append", v)

    def _apply(self, path, op, val):
        # Mirror dedupe: the stream emits each content delta twice.
        if op == "append" and isinstance(val, str):
            if self.last_append.get(path) == val:
                self.dupes_skipped += 1
                self.last_append[path] = None   # allow a genuine 3rd repeat
                return
            self.last_append[path] = val
        try:
            ptr_apply(self.current, path, op, val)
            self.patches += 1
        except Exception:
            pass


# ── generic shape-based fallback (survives field renames) ───────────────────
URLK = re.compile(r"^(url|link|href|source_url|canonical_url|page_url)$", re.I)
TITLEK = re.compile(r"^(title|name|page_title|headline)$", re.I)


def shape_sources(node, out, path="$"):
    if isinstance(node, dict):
        url = next((v for k, v in node.items()
                    if URLK.match(k) and isinstance(v, str) and v.startswith("http")), None)
        title = next((v for k, v in node.items()
                      if TITLEK.match(k) and isinstance(v, str)), None)
        if url and title:
            out.append({"url": url, "title": title, "found_at": path, "raw": node})
        for k, v in node.items():
            shape_sources(v, out, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            shape_sources(v, out, f"{path}[{i}]")


TRACKING_RE = re.compile(r"[?&](utm_[a-z]+|ref|ref_src|si|feature)=[^&]*", re.I)


def canonical(u: str) -> str:
    """Strip tracking params so ?utm_source=chatgpt.com duplicates collapse."""
    if not isinstance(u, str):
        return u
    out = TRACKING_RE.sub("", u)
    out = re.sub(r"\?&", "?", out).rstrip("?&")
    return out


def collect(node, pred, out, path="$"):
    if isinstance(node, dict):
        if pred(node):
            out.append((path, node))
        for k, v in node.items():
            collect(v, pred, out, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            collect(v, pred, out, f"{path}[{i}]")


def main() -> int:
    raw_path = sys.argv[1] if len(sys.argv) > 1 else "capture/chatgpt_raw.txt"
    outdir = sys.argv[2] if len(sys.argv) > 2 else "out"
    os.makedirs(outdir, exist_ok=True)

    try:
        text = open(raw_path, encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        print(f"ERROR: {raw_path} not found. Capture the stream first.")
        return 1

    objs = list(frames(text))
    if not objs:
        print("ERROR: no JSON frames parsed — run inventory.py to inspect.")
        return 1

    ra = Reassembler()
    for o in objs:
        ra.feed(o)
    print(f"frames={len(objs)}  messages={len(ra.messages)}  "
          f"patches_applied={ra.patches}  mirrored_dupes_skipped={ra.dupes_skipped}")

    # ── fan-out queries ─────────────────────────────────────────────────────
    fo = []
    for o in objs:
        collect(o, lambda d: d.get("type") == "search_model_queries", fo)
    fanout, seen = [], set()
    for _, d in fo:
        for q in d.get("queries") or []:
            if q not in seen:
                seen.add(q)
                fanout.append(q)

    # ── retrieved set ───────────────────────────────────────────────────────
    sr = []
    for o in objs:
        collect(o, lambda d: d.get("type") == "search_result" and d.get("url"), sr)

    # The stream carries the SAME page twice: once clean, once tagged with
    # ?utm_source=chatgpt.com. Counting both would inflate the retrieved set
    # (45 raw -> ~26 real here), so dedupe on a canonical form.
    retrieved, order, variants = {}, [], collections.defaultdict(set)
    for _, e in sr:
        u = e["url"]
        cu = canonical(u)
        variants[cu].add(u)
        if cu not in retrieved:
            order.append(cu)
            retrieved[cu] = dict(e)
            retrieved[cu]["url"] = cu
        elif len(json.dumps(e, default=str)) > len(json.dumps(retrieved[cu], default=str)):
            keep = retrieved[cu].get("url")
            retrieved[cu].update(e)
            retrieved[cu]["url"] = keep
    for cu, e in retrieved.items():
        e["url_variants"] = sorted(variants[cu])

    if not retrieved:  # field names changed -> fall back to shape matching
        print("  WARN no type=search_result objects; falling back to shape matcher")
        found = []
        for o in objs:
            shape_sources(o, found)
        for s in found:
            retrieved.setdefault(s["url"], s["raw"])
            if s["url"] not in order:
                order.append(s["url"])

    # Index refs from EVERY raw search_result, not just the dedupe winners:
    # the same source appears with different turn_index values (0 in the UI
    # copy, the real turn id in the tool copy), so a single winner would only
    # carry one of them and half the citation joins would silently fail.
    by_ref, by_ref_loose = {}, {}
    for _, e in sr:
        r = e.get("ref_id") or {}
        if isinstance(r, dict) and "ref_index" in r:
            cu = canonical(e["url"])
            by_ref[(r.get("turn_index"), str(r.get("ref_type")), r.get("ref_index"))] = cu
            by_ref_loose[(str(r.get("ref_type")), r.get("ref_index"))] = cu

    # ── cited set ───────────────────────────────────────────────────────────
    cites = []
    for o in objs:
        collect(o, lambda d: d.get("type") == "cite", cites)

    cited_by_url, cited_by_ref, unresolved_refs = {}, {}, []
    for _, c in cites:
        for su in c.get("safe_urls") or []:
            u = su.get("url") if isinstance(su, dict) else su
            if isinstance(u, str):
                cited_by_url.setdefault(canonical(u), []).append(
                    c.get("component_resolution_id"))
        for ent in c.get("entities") or []:
            ref = ent.get("ref")
            if not isinstance(ref, str):
                continue
            m = REF_RE.fullmatch(ref)
            if not m:
                unresolved_refs.append(ref)
                continue
            turn, rtype, idx = int(m.group(1)), m.group(2), int(m.group(3))
            u = by_ref.get((turn, rtype, idx)) or by_ref_loose.get((rtype, idx))
            if u:
                cited_by_ref.setdefault(u, []).append(ref)
            else:
                unresolved_refs.append(ref)

    for u, e in retrieved.items():
        via = []
        if u in cited_by_url:
            via.append("safe_url")
        if u in cited_by_ref:
            via.append("ref_id")
        e["cited"] = bool(via)
        e["cited_via"] = ",".join(via) or None
        e["cite_refs"] = sorted(set(cited_by_ref.get(u, [])))
        e["is_youtube"] = bool(YT_RE.search(u))
        e["domain"] = re.sub(r"^www\.", "", u.split("/")[2]) if "//" in u else None

    # URLs cited but never seen in the retrieval set (ref-only / redirect forms)
    cited_not_retrieved = [u for u in cited_by_url if u not in retrieved]

    # ── answer + reasoning text ─────────────────────────────────────────────
    answer_parts, reasoning_parts = [], []
    for m in ra.messages:
        msg = m.get("message", {}) or {}
        a = msg.get("author") or {}
        c = msg.get("content") or {}
        parts = c.get("parts") or []
        txt = c.get("text") or (parts[0] if parts and isinstance(parts[0], str) else "")
        if not isinstance(txt, str) or not txt.strip():
            continue
        ct = c.get("content_type")
        if a.get("role") == "assistant" and ct == "text" and msg.get("recipient") == "all":
            answer_parts.append(txt)
        elif ct in ("thoughts", "reasoning_recap"):
            reasoning_parts.append(txt)
    answer = "\n\n".join(answer_parts)
    reasoning = "\n\n".join(reasoning_parts)

    # ── YouTube audit ───────────────────────────────────────────────────────
    yt = [e for e in retrieved.values() if e["is_youtube"]]
    present_keys = sorted({k for e in yt for k in e})
    yt_field_audit = {}
    for f in YT_CLAIMED_FIELDS:
        in_entry = any(f in e for e in yt)
        hit = re.search(r'.{0,60}"%s"\s*:.{0,60}' % re.escape(f), text, re.I)
        yt_field_audit[f] = {
            "in_youtube_entry": in_entry,
            "key_anywhere_in_stream": bool(hit),
            # context matters: a bare key hit is often an unrelated ChatGPT
            # field (e.g. message.channel), not YouTube metadata.
            "context_sample": hit.group(0).strip() if hit else None,
        }
    transcript_keys = sorted({m.group(0) for m in TRANSCRIPT_RE.finditer(text)})

    ref_types = collections.Counter(
        str((e.get("ref_id") or {}).get("ref_type")) for e in retrieved.values())

    # ── write ───────────────────────────────────────────────────────────────
    def p(name):
        return os.path.join(outdir, name)

    rows = sorted(retrieved.values(),
                  key=lambda e: (not e["cited"], e.get("domain") or ""))
    n, m_ = len(rows), sum(1 for r in rows if r["cited"])
    pct = f"{m_ / n * 100:.0f}%" if n else "n/a"

    json.dump(rows, open(p("citations.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False, default=str)
    json.dump({"fanout_queries": fanout,
               "cite_objects": len(cites),
               "unresolved_refs": sorted(set(unresolved_refs)),
               "cited_urls_not_in_retrieved_set": cited_not_retrieved},
              open(p("fanout_queries.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    json.dump({"youtube_results": yt,
               "keys_present_on_youtube_entries": present_keys,
               "claimed_field_audit": yt_field_audit,
               "transcript_shaped_keys_in_raw_stream": transcript_keys},
              open(p("youtube_snapshot.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False, default=str)
    open(p("answer.txt"), "w", encoding="utf-8").write(answer)
    open(p("reasoning.txt"), "w", encoding="utf-8").write(reasoning)

    with open(p("citations.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["cited", "cited_via", "domain", "ref_type", "ref_index",
                     "title", "url", "pub_date", "snippet_len", "is_youtube"])
        for r in rows:
            rid = r.get("ref_id") or {}
            wr.writerow([r["cited"], r.get("cited_via") or "", r.get("domain") or "",
                         rid.get("ref_type", ""), rid.get("ref_index", ""),
                         (r.get("title") or "")[:120], r["url"], r.get("pub_date", ""),
                         len(r.get("snippet") or ""), r["is_youtube"]])

    with open(p("retrieved_vs_cited.md"), "w", encoding="utf-8") as fh:
        W = fh.write
        W("# Retrieved vs Cited — one ChatGPT query\n\n")
        W(f"- **Fan-out sub-queries issued:** {len(fanout)}\n")
        W(f"- **Sources retrieved:** {n}\n")
        W(f"- **Sources cited in the final answer:** {m_}\n")
        W(f"- **Retrieved -> cited conversion:** {pct}\n")
        W(f"- **Citation (`type: cite`) objects:** {len(cites)}\n")
        W(f"- **YouTube sources retrieved:** {len(yt)} "
          f"(cited: {sum(1 for e in yt if e['cited'])})\n")
        W(f"- **ref_type distribution:** "
          f"{', '.join(f'{k}={v}' for k, v in ref_types.most_common())}\n")
        W(f"- **Transcript-shaped keys in raw stream:** "
          f"{', '.join(transcript_keys) if transcript_keys else 'NONE'}\n\n")

        W("## Fan-out queries\n\nThe UI never displays these; they exist only in the stream.\n\n")
        W("\n".join(f"{i}. `{q}`" for i, q in enumerate(fanout, 1)) or "_none found_")

        W("\n\n## YouTube field audit\n\n")
        W("Fields the \"ChatGPT Retrieval Leak\" writeup reports for YouTube sources, "
          "checked against this capture:\n\n")
        W("| claimed field | on a YouTube entry | key anywhere in stream | context if found |\n")
        W("|---|---|---|---|\n")
        for f, a in yt_field_audit.items():
            ctx = (a.get("context_sample") or "").replace("|", "/")[:70]
            W(f"| `{f}` | {'YES' if a['in_youtube_entry'] else 'no'} | "
              f"{'YES' if a['key_anywhere_in_stream'] else 'no'} | "
              f"{('`' + ctx + '`') if ctx else ''} |\n")
        W(f"\nKeys actually present on YouTube entries: "
          f"{', '.join('`%s`' % k for k in present_keys)}\n")

        if cited_not_retrieved:
            W("\n## Cited URLs absent from the retrieval set\n\n")
            for u in cited_not_retrieved:
                W(f"- {u}\n")

        W("\n## Sources\n\n")
        W("`cited_via`: **safe_url** = URL listed in a `type:cite` object; "
          "**ref_id** = resolved from an `entities[].ref` such as `turn828649search4` "
          "back to this entry's `ref_id.ref_index`.\n\n")
        W("| cited | via | domain | ref | title | url |\n|---|---|---|---|---|---|\n")
        for r in rows:
            rid = r.get("ref_id") or {}
            W(f"| {'**YES**' if r['cited'] else 'no'} | {r.get('cited_via') or ''} | "
              f"{r.get('domain') or ''} | {rid.get('ref_type','')}{rid.get('ref_index','')} | "
              f"{(r.get('title') or '')[:60].replace('|','/')} | {r['url']} |\n")

    print(f"\n>>> {len(fanout)} fan-out queries")
    print(f">>> {n} retrieved -> {m_} cited ({pct})")
    print(f">>> {len(yt)} YouTube sources retrieved, "
          f"{sum(1 for e in yt if e['cited'])} cited")
    print(f">>> ref_types: {dict(ref_types)}")
    print(f">>> transcript keys: {transcript_keys or 'NONE'}")
    print(f">>> answer {len(answer)} chars | reasoning {len(reasoning)} chars")
    print(f">>> wrote {outdir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
