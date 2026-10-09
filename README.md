# Beyond Labs — ChatGPT Retrieval Leak

Capturing ChatGPT's streamed network response for a single web-search query, and extracting the
citation snapshots and fan-out sub-queries that the UI never displays.

**Scope:** ChatGPT only, free account, one prompt, one conversation. ~90 minutes.
**Full write-up:** [`NOTES.md`](./NOTES.md) ← start here
**Headline numbers:** [`out/retrieved_vs_cited.md`](./out/retrieved_vs_cited.md)

---

## Results

| Metric | Value |
|---|---|
| Fan-out sub-queries issued for one prompt | **2** |
| Sources retrieved | **25** |
| Sources cited in the final answer | **7** |
| **Retrieved → cited conversion** | **28%** |
| YouTube retrieved / cited | 2 / 1 |
| `ref_type` classes observed | `search` (21), `youtube` (2), `reddit` (2) |
| YouTube rich metadata (channel/followers/views/likes/description) | **absent — did not reproduce** |

**Prompt:** `best project management tools for small agencies in 2026 — include what recent YouTube reviews say`
**Captured:** `chatgpt.com/backend-api/f/conversation` — 377,242 bytes, 19.89 s, model `gpt-6`

---

## Repo layout

```
capture/
  interceptor.js        console snippet — tees the fetch ReadableStream so the
                        page renders normally while a byte-exact copy accumulates
  chatgpt_raw.txt       the captured stream (redacted — see note below)
parse/
  inventory.py          discovery pass: assumes ZERO field names, reports frame
                        shapes, type discriminators, biggest arrays, every URL
  parse_chatgpt.py      extractor: stateful JSON-pointer reassembly + shape-based
                        source matching + two-way retrieved/cited join
out/
  retrieved_vs_cited.md headline stats, fan-out queries, YouTube field audit
  citations.json/.csv   Task 1 — every retrieved source + metadata + cited flag
  fanout_queries.json   Task 2 — sub-queries + join diagnostics
  youtube_snapshot.json the 14-field YouTube audit
  key_inventory.txt     output of the discovery pass
  answer.txt            reassembled answer text
fixtures/
  synthetic_stream.txt  INVENTED fixture used only to smoke-test the scripts.
                        Not evidence of anything.
NOTES.md                the submission write-up
APPROACH.md             the phase-by-phase plan this was executed against
```

## Reproduce

```bash
# 1. paste capture/interceptor.js into the DevTools console on chatgpt.com
#    BEFORE sending your prompt, then: __tapStatus() and __dumpBiggest()

# 2. discovery pass — read this before parsing anything
python3 parse/inventory.py capture/chatgpt_raw.txt | tee out/key_inventory.txt

# 3. extract
python3 parse/parse_chatgpt.py capture/chatgpt_raw.txt out

# 4. headline
cat out/retrieved_vs_cited.md
```

Python 3 standard library only. No dependencies.

## Three things that break a naive parser

1. **Hybrid framing.** Half the frames are JSON-patch deltas (`{"o":"append","p":"/message/content/parts/0","v":"..."}`) that mutate a message announced earlier. Line-by-line parsing silently drops them.
2. **Every delta is sent twice** — once live, once via a revision mirror. Without dedupe the reassembled answer is literally doubled.
3. **Citations are not `citeturn0search3`.** That string appears zero times. The real scheme is inline `<Cite refs={[...]}/>` plus `type:"cite"` objects whose `entities[].ref` (e.g. `turn828649search4`) resolves against each source's `ref_id.ref_index`.

This is why the extractor matches sources by **shape**, not by hardcoded field path, and why `inventory.py` runs first.

## Redaction note

`capture/chatgpt_raw.txt` is the real captured stream with six JWTs (a
`resume_conversation_token` and ad-unit payloads) and internal infrastructure
addresses replaced by `[REDACTED-*]` placeholders. No access tokens, cookies,
API keys or email addresses were present in the capture. All extraction results
are byte-identical before and after redaction.
