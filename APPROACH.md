# Beyond Labs — Interview Task: Execution Plan

**Scope decision (deliberate):** ChatGPT only, one prompt, one conversation. No other platforms.
The brief explicitly permits this — *"You do not have to finish everything. Partial work is completely
fine."* and *"If you can do it locally for one query, share that result and explain your approach for
how you would scale it into a full system."*

The cross-platform "Main task" is therefore answered as a **written method + design section**, not as
captures. Its third bullet (*"Can the same extraction be automated into a repeatable script or
workflow?"*) is fully satisfied by the working parser built in Phase 3. See
[§8 Main Task — written answer](#8-main-task--written-answer) for exactly what to write and how to
frame the gap honestly.

**Total budget: 90 minutes.** Every phase has a hard stop rule. Obey them — a stopped phase with a
documented gap scores better than an overrun phase that eats the write-up.

---

## ✅ Phase 0 is already done — your clock starts at Phase 1

Scaffolding and tooling are written and smoke-tested, so the 90 minutes starts at the capture step.

| File | Status |
|---|---|
| `capture/interceptor.js` | ✅ written — paste into the console |
| `parse/inventory.py` | ✅ written, smoke-tested |
| `parse/parse_chatgpt.py` | ✅ written, smoke-tested |
| `fixtures/synthetic_stream.txt` | ✅ fake stream used to prove the scripts run |
| `capture/`, `parse/`, `out/`, `shots/` | ✅ created |

> **About the fixture:** `fixtures/synthetic_stream.txt` is **invented** — made-up field names and
> made-up values, built only to prove the two scripts execute end-to-end without crashing. It is
> **not** evidence of ChatGPT's real payload shape, and nothing from it should ever appear in your
> submission as a finding. Delete it before sharing if you want zero chance of confusion.

### Runbook — the whole task in five commands

```bash
cd "/home/vatsalyaroy/Desktop/New Folder/beyond-assignment"

# 1. (browser) paste capture/interceptor.js into the console, send the prompt,
#    then run __tapStatus() and __dumpTap()
mv ~/Downloads/chatgpt_raw.txt capture/chatgpt_raw.txt

# 2. recon the payload — READ this output, do not skip it
python3 parse/inventory.py capture/chatgpt_raw.txt | tee out/key_inventory.txt

# 3. extract
python3 parse/parse_chatgpt.py capture/chatgpt_raw.txt out

# 4. the headline
cat out/retrieved_vs_cited.md

# 5. the YouTube finding
jq -r '.[0] | keys_unsorted' out/youtube_snapshot.json
grep -oiE '"[a-z_]*(transcript|caption|subtitle|srt|vtt)[a-z_]*"' capture/chatgpt_raw.txt | sort -u
```

Re-run the smoke test any time (confirms the scripts work before you trust them on real data):

```bash
python3 parse/parse_chatgpt.py fixtures/synthetic_stream.txt /tmp/fixture_out
# expect: 3 fan-out queries | 4 retrieved -> 3 cited (75%) | 1 YouTube source
```

---

## 0. The prompt

```
best project management tools for small agencies in 2026 — include what recent YouTube reviews say
```

**Why this one:**
- It reuses the brief's own example query (`"best project management tools for small agencies"`), so
  the reviewer recognises it instantly.
- `2026` makes it recency-gated, so web search *must* fire — the model can't answer from weights.
- `include what recent YouTube reviews say` is the highest-probability lever for pulling **video
  sources into the retrieval set**. The YouTube description-not-transcript finding is the headline you
  need to reproduce, so the prompt has to make video retrieval likely rather than hope for it.

**Backup prompt** (use only if the first returns zero YouTube sources):

```
best budget mirrorless camera for video in 2026 — summarise what recent YouTube reviews say
```

Consumer-gear queries are YouTube-dominated in search results, so video retrieval is near-certain.

### Free-account critical note

Do **not** rely on auto-routing to decide to search. **Click the Search / globe toggle in the
composer before sending.** Free tier does get web search, but the router may answer from weights
instead — and a no-search stream means there is nothing to extract and you have burned your clean
capture window.

---

## 1. File layout

```
beyond-assignment/
├── APPROACH.md                 # this file
├── capture/
│   ├── interceptor.js          # console snippet — tees the stream (§3)
│   └── chatgpt_raw.txt         # THE ARTIFACT. Raw captured stream.
├── parse/
│   ├── inventory.py            # recursive payload recon (§4)
│   └── parse_chatgpt.py        # name-agnostic extractor (§5)
├── fixtures/
│   └── synthetic_stream.txt    # FAKE stream — smoke-test only, not evidence
├── out/
│   ├── key_inventory.txt       # what keys actually exist in the stream
│   ├── citations.json          # Task 1
│   ├── citations.csv           # Task 1, spreadsheet-friendly
│   ├── fanout_queries.json     # Task 2
│   ├── retrieved_vs_cited.md   # Task 2, the headline statistic
│   ├── youtube_snapshot.json   # the headline finding
│   └── answer.txt              # reassembled answer text (verify markers here)
├── shots/                      # screenshots
└── NOTES.md                    # the submission text (→ pasted into the Google Doc)
```

---

## 2. Phase 0 — Scaffold and arm the capture · ✅ DONE

| | |
|---|---|
| **Goal** | Everything ready *before* the one irreversible step |
| **Artifact** | Directory tree + all three scripts, smoke-tested |
| **Status** | **Complete.** Files are on disk; the scripts have been run against a fixture. |

### Remaining 2 minutes of browser prep — do this immediately before Phase 1

1. Open `capture/interceptor.js`, select all, copy.
2. Open a **fresh ChatGPT tab** (logged in). `F12` → **Console** → type `allow pasting` → paste the
   interceptor → confirm you see `[tap] installed`.
3. Switch to the **Network** tab → filter box: `conversation` → tick **Preserve log**.
4. In the composer, **turn the Search / globe toggle ON**.
5. **Do not send the prompt yet** — read §3 first so you know what to watch for.

> **Why Phase 0 was worth front-loading:** every minute spent writing a parser is a minute the
> browser session is idle. Scaffolding first means the clock only runs on work that needs the live
> session. Hand mechanical file-writing to an AI assistant while you drive the browser — effective
> AI-tool use is an explicitly graded rubric line, and this is the clearest place to demonstrate it.

---

## 3. Phase 1 — Capture the stream · `5–18 min`

| | |
|---|---|
| **Goal** | Get the raw streamed response body onto disk. **This is the only step you cannot redo later.** |
| **Artifact** | `capture/chatgpt_raw.txt` — expect roughly 100 KB – 2 MB |
| **Stop rule** | No search data by **:18** → switch to the backup prompt. Still nothing by **:24** → document it as a failure, proceed with whatever you have. Do not spend 40 minutes here. |

Run **both** capture methods on the same send. Belt and braces — the interceptor is the impressive
one, the DevTools copy is the one that always works.

### Method A — console interceptor (primary)

Paste `capture/interceptor.js` into the DevTools **Console** *before* sending the prompt. Chrome will
refuse the first paste and ask you to type `allow pasting` — do that, then paste again.

Then: send the prompt (Search toggle ON). Wait for the answer to finish rendering. Then run:

```js
__dumpTap()
```

It downloads a `.txt` to `~/Downloads`. Move it:

```bash
mv ~/Downloads/chatgpt_raw.txt capture/chatgpt_raw.txt
wc -c capture/chatgpt_raw.txt
```

**`capture/interceptor.js`:**

> **This now lives on disk at `capture/interceptor.js`** — written and ready. The on-disk
> version is richer than an inline snippet: it also shims `XMLHttpRequest` and `EventSource`
> as a best-effort fallback (in case the client is not using `fetch`), and adds three helpers:
>
> | Helper | What it does |
> |---|---|
> | `__tapStatus()` | `console.table` of every tapped request + char counts. If empty, prints a diagnostic checklist. |
> | `__dumpTap()` | Downloads **all** captured requests to `chatgpt_raw.txt`. |
> | `__dumpBiggest()` | Downloads only the largest stream — use this if several requests got tapped. |
>
> Open the file and copy the whole thing into the console.

**Why this is worth doing rather than just copy-pasting from DevTools** — say this on camera:
- `res.body.tee()` splits the `ReadableStream` into two independent branches. The page consumes one
  and renders normally; we drain the other. Nothing is consumed twice, nothing is blocked.
- `TextDecoder` with `{ stream: true }` correctly handles a multi-byte UTF-8 character split across a
  chunk boundary — a naive `new TextDecoder().decode(chunk)` per chunk corrupts those.
- It must be injected **before** the request fires. That is a real constraint worth naming: it is why
  a page-load-time request would need an extension injecting at `document_start` in the MAIN world
  instead of a console paste.

**Known limitation to state honestly:** this only taps `fetch`. If the client used `XMLHttpRequest`,
`EventSource`, or a WebSocket, nothing is captured — that is exactly what Method B covers.

### Method B — DevTools copy (fallback, always works)

Network panel → click the `conversation` request → **EventStream** tab (if present) or **Response**
tab → select all → copy → paste into `capture/chatgpt_raw.txt`.

> **Trap worth mentioning in the write-up:** "Save all as HAR with content" generally does **not**
> preserve streamed/SSE response bodies — you get the request with empty content. Knowing that before
> wasting five minutes on it is the kind of thing the network-inspection rubric line is testing.

### Screenshots to take now (you cannot get these back)

1. The Network panel **mid-stream**, with the `conversation` request selected. ← most valuable frame
2. The EventStream / Response tab showing raw `data:` frames.
3. The console showing `[tap] ... chars` confirming the capture size.
4. The final rendered answer with its visible citation chips.

Save to `shots/`.

---

## 4. Phase 2 — Recon the payload. Do not parse yet. · `18–30 min`

| | |
|---|---|
| **Goal** | **Discover** where the data lives instead of guessing field names |
| **Artifact** | `out/key_inventory.txt` |
| **Stop rule** | **:30** |

This is the phase that separates a solid submission from a lucky one, and it is the one to narrate on
camera. Two things make this stream harder than "parse the JSON":

1. **It is not uniform JSON.** The stream mixes complete message objects with compact
   **JSON-patch-style delta frames** — small objects carrying a *path*, an *operation*
   (`append`/`replace`/`add`), and a *value*, which mutate an object sent earlier. A naive
   line-by-line `json.loads` parser reads each frame in isolation and **silently drops** everything
   that only ever exists as a patch. You will see this in the inventory output as a large population
   of tiny frames with 2–3 keys.
2. **Field names are undocumented and drift.** Anything anyone tells you about the exact key names —
   including this document — is a hypothesis until your own payload confirms it. So the parser is
   built name-agnostic (§5) and the inventory tells you what is actually there.

### Steps

```bash
python3 parse/inventory.py capture/chatgpt_raw.txt | tee out/key_inventory.txt
less out/key_inventory.txt    # actually READ it — this is the deciding step
```

**`parse/inventory.py`:**

> **This now lives on disk at `parse/inventory.py`** — written and smoke-tested. Beyond the
> description above, the on-disk version also prints:
>
> - a **PATCH-LIKE FRAMES** percentage with an explicit verdict telling you whether the
>   reassembly pass is required for *your* capture
> - a dedicated **YOUTUBE URLS** section
> - a **TRANSCRIPT-SHAPED KEYS** grep over the whole raw file (expected: none — that absence
>   is the headline finding, pre-computed for you)
> - a diagnostic hint if zero frames parse

### What to look for in the output — and what it tells you

| Signal in the inventory | What it means |
|---|---|
| Many frames whose key set is 2–3 short keys | The **delta/patch format** is in play. Your parser must reassemble, not read line-by-line. |
| One array with 20–60 entries, each containing a URL + a title + a long string | The **retrieved set** (Task 1 + the "retrieved" half of Task 2). |
| Short strings that read like search phrases, near a tool/recipient discriminator | The **fan-out queries** (Task 2). |
| Strings in the answer text matching a `turn<N>search<M>`-style reference pattern | The **citation markers**. Parsing this scheme *is* the retrieved↔cited join key. |
| `youtube.com` / `youtu.be` URLs, and nearby keys about channel / views / likes / followers | The **YouTube snapshot** (§7, the headline). |
| Strings over ~1000 chars containing `0:00`-style timecodes | A YouTube **description** with chapters preserved. |

Note the distinct URL count now — it is your "retrieved" denominator.

---

## 5. Phase 3 — Parser: Task 1 + Task 2 · `30–52 min`

| | |
|---|---|
| **Goal** | Both explicit tasks, done |
| **Artifacts** | `out/citations.json`, `out/citations.csv`, `out/fanout_queries.json`, `out/retrieved_vs_cited.md` |
| **Stop rule** | **:52** — ship what parses, write the gaps into the failure log |

Build it in this priority order, so that running out of time degrades gracefully:

1. **Retrieved set** — every source with `url / title / snippet / publish date / domain`.
2. **Fan-out queries** — the sub-searches, in issue order.
3. **Cited set** — the sources actually referenced in the final answer, joined back to (1).

### Design principle: name-agnostic core, discovered config

The extractor finds source records **structurally** — "any object that has a URL-ish value *and* a
title-ish value" — rather than by hardcoded path. Then you pin the specifics using what Phase 2
actually showed you. This is what makes it survive schema drift, and it is the single best engineering
point in the submission.

> **This now lives on disk at `parse/parse_chatgpt.py`** — written and smoke-tested against a
> synthetic fixture. Read it before Phase 3; the tunable regexes are in one block at the top.
>
> **It resolves the retrieved↔cited join two independent ways**, because each alone misses cases:
>
> | Signal | How it works | When it misses |
> |---|---|---|
> | **marker** | Parses `turn<T><kind><N>` refs out of the answer text and resolves `N` as an index into the retrieval set in stream order | If the marker index space does not match stream order (the script warns when an index overruns) |
> | **url** | Checks whether the raw URL appears inline in the answer text | Only fires when the model inlined a bare URL — rare |
>
> Each source gets a `cited_via` field recording which signal matched. **This matters a lot:**
> on the smoke test, URL-matching alone found 1 cited source; adding marker resolution found 3.
> That is the difference between reporting 25% and 75% conversion — i.e. between a wrong
> headline number and a right one.
>
> **The marker-index resolution is a hypothesis, not a verified fact.** Before the number goes
> in the Doc, cross-check it against the citation chips visible in the rendered answer. If the
> counts disagree, say so in the write-up — a stated discrepancy is a finding; a silently wrong
> number is an error.

### Expect to iterate — that is the point

It will not be right first run. Each failure is rubric material: run it, read the counts in the
header line, go back to `out/key_inventory.txt`, adjust a regex, re-run. **Narrate exactly this loop
on camera** — the first rubric line is *"how you break down an unfamiliar problem and debug it."*

Two specific things to verify rather than assume:
- **The patch-frame key names** (`PATH_K / OP_K / VAL_K`). Confirm from the frame-shapes section of
  the inventory. If `patch_paths=0` and `full_objects` equals the frame count, the stream was plain
  full-object JSON — note that and move on.
- **The citation marker scheme.** Read `out/answer.txt` and the raw answer text; find the literal
  marker format; fix `CITE_RE`. If markers index into a per-turn search result list, the index *is*
  the join — resolve marker → retrieved source via that index, which is more accurate than the
  direct-URL substring check the script falls back to.

### The money output

One line, and it is the brief's own thesis reproduced from your own data:

> **N retrieved → M cited (X%).** Lead the Google Doc with this.

---

## 6. Phase 4 — The YouTube snapshot · `52–63 min`

| | |
|---|---|
| **Goal** | Reproduce *"ChatGPT reads your YouTube description, not your transcript"* |
| **Artifact** | `out/youtube_snapshot.json` + an annotated screenshot |
| **Stop rule** | **:63** |

Two claims to prove, and the second is the stronger one:

**(a) What IS there.** Pull every YouTube source and dump its complete raw attribute bag — channel
name, follower/subscriber count, verified flag, views, likes, publish date, and the full description.

```bash
jq '[.[] | select(.url | test("youtube\\.com|youtu\\.be")) | .raw]' \
   out/citations.json > out/youtube_snapshot.json
jq -r '.[0] | keys_unsorted' out/youtube_snapshot.json     # what fields actually arrived
```

**(b) What is NOT there — demonstrate the absence.** Grep the *entire raw stream* for any
transcript-like key or content and show the empty result:

```bash
grep -oiE '"[a-z_]*(transcript|caption|subtitle|cc_|srt|vtt)[a-z_]*"' capture/chatgpt_raw.txt \
  | sort -u
# expected: no output
```

A demonstrated absence is far stronger than a bullet point asserting it. Screenshot the empty grep.

**(c) Timecodes survive.** Check whether chapter timecodes are preserved intact in the description:

```bash
jq -r '.[].description? // empty' out/youtube_snapshot.json | grep -oE '^[0-9]+:[0-9]{2}.*' | head -20
```

If they are, that is the "ChatGPT can read your chapters" point reproduced. (Adjust the `.description`
key to whatever the real one turned out to be.)

**(d) The size argument.** Show that the description is the largest text block the model has about the
video — the LinkedIn post's core claim:

```bash
jq -r '.[] | [(.title|length), (.description|length)] | @tsv' out/youtube_snapshot.json
```

### If there are zero YouTube sources

Do not burn the clock re-rolling prompts. Do this instead, and it still scores:
1. Note it explicitly: "my query's retrieval set contained no video sources."
2. Run the backup prompt **only if you are before :58**.
3. Otherwise write the finding as *expected* and state that confirming it needs a video-heavy query —
   explicitly flagged as untested. Honest, and it costs you almost nothing with this reviewer.

---

## 7. Phase 5 — Write-up · `63–78 min`

| | |
|---|---|
| **Goal** | The actual submission |
| **Artifact** | `NOTES.md` → pasted into the Google Doc |
| **Stop rule** | **:78** |

**Do not polish.** The brief discourages it twice. Bullets and rough prose are correct here.

### Section order — strongest first

A reviewer skims for 90 seconds. Front-load the findings; put the method after.

```markdown
# ChatGPT Retrieval Leak — single-query capture + extraction

**Time spent:** ~90 min · **Scope:** ChatGPT (free account), one prompt, one conversation

## 1. Headline findings
- Prompt: "best project management tools for small agencies in 2026 — include what recent YouTube reviews say"
- **N sources retrieved → M cited in the final answer (X% conversion).** Retrieved ≠ cited, confirmed.
- K fan-out sub-queries issued for one user prompt (listed below).
- YouTube sources arrive with title, channel, followers, verified status, publish date, views, likes
  and the FULL description — and **no transcript field anywhere in the stream** (grep output below).
- Description chapter timecodes survive intact → the model can read your chapter titles.

## 2. Outputs
- citations.json / citations.csv — every retrieved source + metadata + cited flag
- fanout_queries.json — the sub-queries
- retrieved_vs_cited.md — the table and the statistic
- youtube_snapshot.json — the video metadata bag

## 3. How I captured it
- Forced web search via the composer's Search toggle (free tier auto-routing may skip search).
- Injected a fetch interceptor that `tee()`s the response ReadableStream, so the page renders
  normally while a byte-for-byte copy accumulates; dumped to a file.
- Kept the DevTools EventStream copy as a parallel fallback.
- Noted: HAR export does not preserve streamed bodies; the interceptor must be installed before the
  request fires.

## 4. How I parsed it
- The stream is not uniform JSON: full message objects interleaved with JSON-patch-style delta
  frames that mutate earlier objects. A line-by-line parser silently drops patch-only content, so the
  parser reassembles first.
- Field names are undocumented and drift, so the extractor finds source records **structurally**
  (any object carrying a URL-ish value plus a title-ish value) rather than by hardcoded path, and
  I derived the specifics from a key-inventory pass over my own payload.
- Retrieved↔cited join: parsed the citation marker scheme out of the answer text.

## 5. What did not work
(see template below)

## 6. Scope I did not cover, and why
Other platforms (Gemini / Claude / Grok / Perplexity) — see the method + design section.

## 7. How I would scale this to a system
(see §9)

## 8. Main task — cross-platform: method and design
(see §8)

## 9. Tools used
Chrome DevTools, a hand-written fetch interceptor, Python 3 (stdlib only), jq,
Claude Code (Opus) for scaffolding the parser and the recon script while I worked the browser.
```

### Failure-log template

Fill these from what **actually** happened — do not ship a failure you did not have. These are the
likely candidates; delete the ones that did not occur.

| What I tried | What happened | Why | What I did instead | With more time |
|---|---|---|---|---|
| HAR export to get the stream body | Request present, response content empty | Chrome does not persist streamed/SSE bodies into HAR | Wrote a fetch interceptor that tees the stream | Package it as an extension injecting at `document_start` so page-load requests are caught too |
| Line-by-line `json.loads` over every `data:` frame | Most frames parsed but citation/source data was missing | Stream mixes full objects with JSON-patch deltas; patch-only content was being dropped | Added a reassembly pass keyed by patch path | Build a proper JSON-pointer applier rather than a flat path accumulator |
| Hardcoding the field paths I expected | Zero sources extracted | Private undocumented API; my assumed key names did not match this payload | Wrote `inventory.py` to discover real key paths, then matched records by shape | Ship the shape-matcher as the default and treat named paths as an optimisation |
| Asking without the Search toggle | Model answered from weights, no search activity in the stream | Free-tier routing may skip web search | Re-sent with Search explicitly enabled | Detect "no search happened" automatically and retry with the toggle forced |
| `grep` for a transcript field | No matches | ChatGPT genuinely does not receive the transcript | Treated the absence as the finding and screenshotted it | Test across 20 video queries to confirm it is universal, not query-specific |

---

## 8. Main task — written answer

You are not capturing other platforms, so answer the Main task's three bullets as **method and
reasoning**, clearly labelled as untested. Write it roughly like this:

> **Scope note.** I had a free ChatGPT account and no logged-in sessions on the other assistants, so
> I went deep on one platform and one query rather than shallow across four. Below is the method I
> would apply to each, framed as hypotheses to test rather than findings — I have not captured these
> streams, and I would rather flag that than assert it.
>
> **The method transfers unchanged.** Nothing in my approach is ChatGPT-specific:
> 1. Open DevTools → Network, filter to the request that stays open for the duration of the answer
>    (that is the stream), and note its `content-type` — `text/event-stream`, `application/x-ndjson`,
>    chunked JSON, or a WebSocket.
> 2. Install the same `fetch` tee interceptor (plus `XMLHttpRequest` / `EventSource` / `WebSocket`
>    shims if the transport is not `fetch`) and capture the raw body.
> 3. Run `inventory.py` on it. It assumes nothing about field names, so it works on any payload: it
>    reports frame shapes, type discriminators, the biggest arrays, every URL with its key path, and
>    every long string. The retrieval set is almost always "the one big array of objects that each
>    contain a URL, a title and a long snippet."
> 4. Run the shape-based extractor. Only the citation-marker regex and the patch-frame key names are
>    ever platform-specific.
>
> **The axes I would compare on** — and the questions each answers:
>
> | Axis | Why it matters |
> |---|---|
> | Transport (SSE / NDJSON / chunked / WebSocket) | Decides whether a `fetch` tee is even sufficient |
> | State model: cumulative snapshots vs incremental deltas | Decides whether the parser needs a reassembly pass at all — this was the main trap on ChatGPT |
> | Keyed objects vs positional arrays | Google's internal RPC envelopes are notoriously positional and unkeyed, which would force purely shape-based extraction |
> | Fan-out visibility | Are sub-queries streamed to the client, or resolved server-side and never sent? |
> | Retrieved-set visibility | Does the client receive the full retrieval universe, or only the sources that survived into the answer? This is the whole "retrieved ≠ cited" question, and a platform that only ships the cited set cannot answer it. |
> | Per-source metadata richness | Snippet, date, and platform-specific extras (the YouTube bag) |
> | Opaque / encrypted result fields | If result content arrives encrypted or as an opaque blob, snippet extraction is blocked — that is itself a reportable finding rather than a failure |
> | Reasoning visibility | Whether intermediate steps stream to the browser |
>
> **Cheapest next platform:** Perplexity — it answers without a login, so it costs one capture and no
> account. I would do that first with ~10 minutes.
>
> **Can it be automated?** Yes, and it already is — `parse_chatgpt.py` is the repeatable script, and
> `inventory.py` is the tool that bootstraps a new platform adapter. Scaling it to a system is below.

This is an honest, substantive answer to the Main task. It directly satisfies bullet 3 (automation),
and it answers bullets 1–2 as a reasoned method with the gap declared rather than hidden. Per the
brief: *"If you get stuck on one platform, move to the next and tell us what blocked you."*

---

## 9. Scaling design — the section that signals seniority

Make this point the centrepiece, because it is the one a senior engineer makes and a junior one
misses:

> **The hard problem is not capture. It is silent schema drift.** These are undocumented private APIs
> that change without notice, with no versioning and no deprecation window. A pipeline built on
> hardcoded field paths does not fail loudly — it quietly starts returning zero citations, and your
> research dataset develops a hole you only notice weeks later.

### Architecture

```
┌─ Capture ──────────────────────────────────────────────────────────┐
│ Headful Chrome, persistent authenticated profiles (one per         │
│ platform × account), driven over the DevTools Protocol.            │
│ Interceptor injected at document_start in the MAIN world.          │
│ Residential proxy pool — search results are localised, so geo is   │
│ an experimental variable, not an afterthought.                     │
│ Session/cookie refresh + CAPTCHA detection → quarantine the        │
│ profile, alert, do not silently retry into a ban.                  │
└────────────────────────────────────────────────────────────────────┘
          ↓ raw bytes, nothing parsed yet
┌─ Raw store (IMMUTABLE SOURCE OF TRUTH) ────────────────────────────┐
│ Every captured stream → object storage, compressed, keyed          │
│ run_id/platform/date. Never mutated, never deleted.                │
│ WHY: when an adapter turns out to be wrong — and it will — you     │
│ reprocess history instead of re-collecting it. Re-collection is    │
│ impossible: the model, the index and the SERP have all moved on.   │
└────────────────────────────────────────────────────────────────────┘
          ↓
┌─ Normalise ────────────────────────────────────────────────────────┐
│ Versioned per-platform adapters behind one interface, emitting a   │
│ unified schema. Shape-based extractor as the always-available      │
│ fallback when a named-path adapter yields nothing.                 │
└────────────────────────────────────────────────────────────────────┘
          ↓
┌─ Analytics store ──────────────────────────────────────────────────┐
│ Postgres (or DuckDB at small scale): runs, fanout_queries,         │
│ retrieved_sources, cited_sources, youtube_attributes.              │
└────────────────────────────────────────────────────────────────────┘
          ↓
┌─ Research questions this actually answers ─────────────────────────┐
│ • Citation share by domain, tracked over time                      │
│ • Retrieved→cited conversion rate per domain (the real ranking     │
│   signal — being retrieved is cheap, being cited is the prize)     │
│ • Which YouTube attributes correlate with being cited: views,       │
│   followers, verified status, description length, chapter presence  │
│ • Fan-out query patterns: how one prompt becomes K searches        │
└────────────────────────────────────────────────────────────────────┘
```

### Unified schema

```json
{
  "run_id": "2026-10-09T14:22:05Z/chatgpt/a1b2c3",
  "captured_at": "2026-10-09T14:22:05Z",
  "platform": "chatgpt",
  "platform_build": "sha-or-asset-hash-if-observable",
  "account_tier": "free",
  "geo": "IN",
  "prompt": "best project management tools for small agencies in 2026 ...",
  "fanout_queries": [{"order": 1, "query": "...", "tool": "web_search"}],
  "retrieved": [{
    "rank": 3, "url": "...", "canonical_url": "...", "domain": "youtube.com",
    "title": "...", "snippet": "...", "publish_date": "2026-08-14",
    "source_type": "video",
    "youtube": {"channel": "...", "followers": 412000, "verified": true,
                "views": 184233, "likes": 7421,
                "description": "...", "has_timecodes": true,
                "transcript_present": false},
    "raw_attributes": {"__everything_the_platform_sent": "..."}
  }],
  "cited": [{"url": "...", "marker": "...", "answer_char_start": 412, "answer_char_end": 418}],
  "answer_text": "...",
  "reasoning_text": null,
  "raw_blob_ref": "s3://.../2026-10-09/chatgpt/a1b2c3.ndjson.gz",
  "adapter_version": "chatgpt@2026-10-09",
  "extraction_warnings": []
}
```

Two deliberate choices worth calling out: `raw_attributes` keeps **everything** the platform sent, so
a field you did not know mattered is still recoverable later; and `raw_blob_ref` means every
normalised row can be regenerated from source.

### Drift detection (the part most people skip)

1. **Canary assertions per adapter** — every run must yield ≥1 fan-out query, ≥5 retrieved sources,
   ≥1 citation, and a non-empty answer. Violation → alert, quarantine the run, do not write it to
   analytics.
2. **"Zero citations extracted" alarm** — the single highest-value monitor in the system.
3. **Key-inventory diff** — store the set of observed JSON key paths per run; diff against the
   previous run for that platform and alert on newly-appeared or disappeared keys. This catches drift
   *before* it breaks extraction.
4. **Payload shape hash** — a hash over the frame-shape distribution; a step change means the
   platform shipped something.
5. **Automatic fallback** — when a named-path adapter underperforms its canary, re-run through the
   shape-based extractor and flag the row `extraction_warnings: ["fell_back_to_shape_matcher"]`.
   Degraded data, clearly labelled, beats silent zeros.

### n8n variant (the brief mentions it)

Workable as the **orchestration layer**: Cron → HTTP/queue trigger → a container step that drives the
browser capture → a Code node for normalisation → Postgres insert → Slack alert on canary failure.
Where it is the wrong tool: the capture itself. Browser-profile lifecycle, CDP streaming, CAPTCHA
quarantine and proxy rotation are stateful, long-running concerns that want a real service, not a
workflow node. Use n8n for scheduling, alerting and glue; keep capture in code.

### Honest ToS paragraph — include it, it reads as maturity

> This pipeline reads traffic that my own browser already receives on my own account. That is fine for
> research at small scale, but automating logged-in consumer accounts at volume sits against most
> providers' terms, and the transport is undocumented and unversioned — it can change any week. If I
> were building this for a client I would say plainly: treat the pipeline as a research instrument
> with an expected maintenance cost, not as infrastructure. Budget for adapter breakage, keep the raw
> blobs so history is reprocessable, respect rate limits, prefer official APIs wherever they expose
> the same data, and keep the capture volume proportionate to the research question.

---

## 10. Phase 6 — Loom + ship · `78–90 min`

### Loom shot list (target 7 minutes, 10 max)

Have these open in tabs before you hit record: the ChatGPT conversation with DevTools open,
`out/key_inventory.txt`, `out/retrieved_vs_cited.md`, `out/youtube_snapshot.json`, a terminal.

| Time | On screen | What to say |
|---|---|---|
| **0:00–0:40** | The brief, then your results dir | "The task was to capture ChatGPT's network stream and pull out the citation snapshots and fan-out queries. I had a free account, so I made a deliberate call: one platform, one query, go deep, and treat the cross-platform part as a written design. Here's what I found." |
| **0:40–1:20** | `out/retrieved_vs_cited.md` | **Lead with the number.** "For one prompt, ChatGPT ran **K sub-searches**, retrieved **N sources**, and cited **M** of them in the final answer — a **X%** conversion. That's the 'retrieved is not cited' claim, reproduced from my own capture." |
| **1:20–2:40** | Live ChatGPT + DevTools Network | "Here's the capture. I forced the Search toggle on, because on free tier the router may answer from weights and then there's no search activity in the stream at all. This one request stays open for the whole answer — that's the stream." Show the EventStream frames scrolling. |
| **2:40–3:30** | `capture/interceptor.js` in the console | "I didn't want to copy-paste out of DevTools, so I wrapped `fetch` and used `tee()` on the response stream — the page gets one branch and renders normally, I drain the other. One subtlety: the decoder has to be in streaming mode, or a multi-byte character split across a chunk boundary gets corrupted. Also, HAR export does **not** save streamed bodies — that cost me a few minutes." |
| **3:30–4:50** | `out/key_inventory.txt` | **The debug moment — spend real time here.** "My first parser got almost nothing. The reason is this: the stream isn't uniform JSON. It's full message objects interleaved with JSON-patch-style delta frames that mutate objects sent earlier. Read line-by-line, everything that only exists as a patch just vanishes. So I wrote this recon script first — it assumes nothing about field names and just tells me what shapes and key paths are actually in there. Then I reassemble, then I parse." |
| **4:50–5:40** | `parse_chatgpt.py`, then `out/citations.json` | "Second design decision: these are undocumented private APIs, the key names drift. So the extractor finds source records by **shape** — any object with a URL-ish value and a title-ish value — rather than by hardcoded path. Here's the output: every retrieved source with url, title, snippet, date, domain, and a cited flag." |
| **5:40–6:40** | `out/youtube_snapshot.json`, then the grep | "And here's the YouTube finding. Title, channel, follower count, verified status, publish date, views, likes, and the complete description — with the chapter timecodes intact. Now watch this: I grep the entire raw stream for anything transcript-shaped. **Nothing.** ChatGPT never receives the transcript. The description is the largest block of text it has about the video, which is exactly why it matters so much." |
| **6:40–7:20** | The architecture sketch | "On scaling: the hard part isn't capture, it's silent schema drift. These APIs change with no notice and a hardcoded parser doesn't crash — it quietly returns zero citations and you get a hole in your dataset. So: raw blobs to object storage as immutable source of truth, versioned adapters, canary assertions per run, a key-inventory diff that alerts on new or vanished keys, and automatic fallback to the shape matcher. Degraded-but-labelled beats silent zeros." |
| **7:20–7:45** | `NOTES.md` failure log | "What didn't work is written up here. **90 minutes**, tools were Chrome DevTools, a hand-written fetch interceptor, Python stdlib, jq, and Claude Code to scaffold the scripts while I worked the browser. If I had more time: the other four platforms, and twenty video queries to check whether the no-transcript result is universal or just my query." |

**Delivery notes:** do not re-record for small stumbles — the brief says *keep it rough*. Say the
headline number inside the first 60 seconds. Spend the most time on the 3:30–4:50 debug segment;
that is the highest-scoring 80 seconds in the whole video, because the top rubric line is problem
breakdown and debugging.

### Ship

1. New Google Doc → paste `NOTES.md` → drop in screenshots from `shots/` → Loom link at the top.
2. Code: paste `interceptor.js`, `inventory.py`, `parse_chatgpt.py` into the Doc *or* link a Gist.
   Also paste `retrieved_vs_cited.md` inline — a reviewer should not have to click to see results.
3. Share as **Editor** with `sachin@beyondlabs.io` and `business@beyondlabs.io`.
4. Reply on the **existing email thread**, **subject unchanged**, with the Doc link.
5. State your real time. If you ran to 105 minutes, say 105.

---

## 11. Cut list — drop in this order if behind

1. `citations.csv` → JSON only
2. Timecode-preservation check (§6c) and the description-size argument (§6d)
3. The cross-platform written section (§8) → compress to three sentences
4. The architecture diagram → keep the drift-detection paragraph, it carries the whole point
5. **Never cut:** the raw capture, the retrieved→cited number, the YouTube grep, the failure log

---

## 12. Biggest risk

**The free-tier account does not fire a web search, or fires one with no YouTube sources in the
retrieval set.**

Mitigation: force the Search toggle manually; have the backup prompt ready; obey the Phase 1 stop
rule at **:18**. If YouTube sources never appear, §6's "zero YouTube sources" path still produces a
complete, honest submission — the retrieved-vs-cited statistic alone satisfies both explicit tasks.

**Second risk: over-polishing.** The brief discourages polish twice and explicitly rewards showing
what failed. An unpolished submission with a real failure log and a real number beats a tidy one
without them.
