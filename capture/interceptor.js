/* ───────────────────────────────────────────────────────────────────────────
   ChatGPT stream tap — paste into the DevTools Console on chatgpt.com
   BEFORE sending your prompt.

   Chrome blocks the first console paste: type  allow pasting  then paste again.

   How it works
   ------------
   Wraps window.fetch. When a response looks like the answer stream, we call
   res.body.tee() to split the ReadableStream into two independent branches:
   one is handed back to the page (so the UI renders normally), the other we
   drain into a buffer. Nothing is consumed twice and nothing is blocked.

   TextDecoder runs in streaming mode so a multi-byte UTF-8 character split
   across a chunk boundary is reassembled instead of corrupted.

   Usage
   -----
     1. paste this                 → "[tap] installed"
     2. send your prompt (Search toggle ON)
     3. wait for the answer to finish rendering
     4. __tapStatus()              → see what was captured
     5. __dumpTap()                → downloads chatgpt_raw.txt

   Known limitation: this only taps fetch(). If the client used
   XMLHttpRequest / EventSource / WebSocket, nothing is captured here — fall
   back to the DevTools EventStream tab. (XHR + EventSource shims are
   installed below as a best-effort extra.)
   ─────────────────────────────────────────────────────────────────────────── */

(() => {
  if (window.__tap) {
    console.log('[tap] already installed — run __tapStatus() or __dumpTap()');
    return;
  }

  const store = (window.__tap = {});
  const meta = (window.__tapMeta = {});
  let n = 0;

  const WORTH_URL = /conversation|backend-api|\/f\/|chat|completion|stream/i;
  const WORTH_CT = /event-stream|x-ndjson|ndjson|octet-stream/i;

  function record(kind, url, text) {
    const key = `#${String(++n).padStart(2, '0')} [${kind}] ${url.split('?')[0]}`;
    store[key] = text || '';
    meta[key] = { kind, url, startedAt: new Date().toISOString() };
    return key;
  }

  /* ── fetch ───────────────────────────────────────────────────────────── */
  const origFetch = window.fetch;

  window.fetch = async function (...args) {
    const res = await origFetch.apply(this, args);
    try {
      const a0 = args[0];
      const url = typeof a0 === 'string' ? a0 : (a0 && a0.url) || '';
      const ct = res.headers.get('content-type') || '';
      const worth = WORTH_URL.test(url) || WORTH_CT.test(ct);
      const wrappable = res.body && ![204, 205, 304].includes(res.status);

      if (worth && wrappable) {
        const key = record('fetch', url, '');
        meta[key].contentType = ct;
        meta[key].status = res.status;

        const [toPage, toUs] = res.body.tee();

        // Drain our branch independently — never await this.
        (async () => {
          const dec = new TextDecoder('utf-8');
          const rdr = toUs.getReader();
          try {
            for (;;) {
              const { value, done } = await rdr.read();
              if (done) break;
              store[key] += dec.decode(value, { stream: true });
            }
            store[key] += dec.decode(); // flush any trailing partial char
          } catch (e) {
            console.warn('[tap] drain aborted for', key, e);
          }
          meta[key].bytes = store[key].length;
          meta[key].endedAt = new Date().toISOString();
          console.log(`[tap] ${key} → ${store[key].length.toLocaleString()} chars`);
        })();

        return new Response(toPage, {
          status: res.status,
          statusText: res.statusText,
          headers: res.headers,
        });
      }
    } catch (e) {
      console.warn('[tap] passthrough after error:', e);
    }
    return res;
  };

  /* ── XMLHttpRequest (best effort) ────────────────────────────────────── */
  const OrigXHR = window.XMLHttpRequest;
  if (OrigXHR) {
    const origOpen = OrigXHR.prototype.open;
    const origSend = OrigXHR.prototype.send;
    OrigXHR.prototype.open = function (method, url, ...rest) {
      this.__tapUrl = String(url || '');
      return origOpen.call(this, method, url, ...rest);
    };
    OrigXHR.prototype.send = function (...a) {
      if (WORTH_URL.test(this.__tapUrl || '')) {
        const key = record('xhr', this.__tapUrl, '');
        this.addEventListener('progress', () => {
          try {
            store[key] = this.responseText || store[key];
          } catch (_) {
            /* responseType may not be text */
          }
        });
        this.addEventListener('loadend', () => {
          try {
            store[key] = this.responseText || store[key];
          } catch (_) {}
          meta[key].bytes = store[key].length;
          console.log(`[tap] ${key} → ${store[key].length.toLocaleString()} chars`);
        });
      }
      return origSend.apply(this, a);
    };
  }

  /* ── EventSource (best effort) ───────────────────────────────────────── */
  const OrigES = window.EventSource;
  if (OrigES) {
    window.EventSource = function (url, cfg) {
      const es = new OrigES(url, cfg);
      const key = record('eventsource', String(url), '');
      es.addEventListener('message', (ev) => {
        store[key] += `data: ${ev.data}\n\n`;
        meta[key].bytes = store[key].length;
      });
      return es;
    };
    window.EventSource.prototype = OrigES.prototype;
  }

  /* ── helpers ─────────────────────────────────────────────────────────── */
  window.__tapStatus = () => {
    const rows = Object.keys(store).map((k) => ({
      request: k,
      chars: store[k].length,
      contentType: meta[k].contentType || '',
    }));
    if (!rows.length) {
      console.warn(
        '[tap] nothing captured yet.\n' +
          '  • Did you send the prompt AFTER pasting this?\n' +
          '  • Did the answer actually stream (vs render instantly from cache)?\n' +
          '  • If still empty, use the DevTools EventStream tab instead.'
      );
    } else {
      console.table(rows);
    }
    return rows;
  };

  window.__dumpTap = (name = 'chatgpt_raw.txt') => {
    const keys = Object.keys(store);
    if (!keys.length) {
      console.warn('[tap] nothing to dump — run __tapStatus() first');
      return;
    }
    const body = keys
      .map((k) => `===== ${k} =====\n${store[k]}`)
      .join('\n\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([body], { type: 'text/plain' }));
    a.download = name;
    a.click();
    console.log(
      `[tap] dumped ${body.length.toLocaleString()} chars from ${keys.length} request(s) → ${name}`
    );
  };

  // Largest captured stream only — handy when several requests were tapped.
  window.__dumpBiggest = (name = 'chatgpt_raw.txt') => {
    const keys = Object.keys(store);
    if (!keys.length) return console.warn('[tap] nothing captured');
    const best = keys.reduce((a, b) => (store[a].length >= store[b].length ? a : b));
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([store[best]], { type: 'text/plain' }));
    a.download = name;
    a.click();
    console.log(`[tap] dumped ${best} (${store[best].length.toLocaleString()} chars) → ${name}`);
  };

  // FALLBACK when Chrome blocks the programmatic download: puts the biggest
  // captured stream on the clipboard via the DevTools `copy()` helper, so you
  // can paste straight into capture/chatgpt_raw.txt.
  window.__copyTap = () => {
    const vals = Object.values(store);
    if (!vals.length) return console.warn('[tap] nothing captured');
    const biggest = vals.sort((a, b) => b.length - a.length)[0];
    if (typeof copy === 'function') {
      copy(biggest); // DevTools-only global
      console.log(`[tap] ${biggest.length.toLocaleString()} chars on the clipboard — paste into capture/chatgpt_raw.txt`);
    } else {
      console.warn('[tap] copy() unavailable; use __dumpTap() or read window.__tap directly');
    }
    return biggest.length;
  };

  console.log(
    '%c[tap] installed.',
    'color:#0a0;font-weight:bold',
    '\n  1. send your prompt with the Search toggle ON' +
      '\n  2. wait for the answer to finish' +
      '\n  3. __tapStatus()   then   __dumpTap()' +
      '\n     (download blocked? use __copyTap() instead)'
  );
})();
