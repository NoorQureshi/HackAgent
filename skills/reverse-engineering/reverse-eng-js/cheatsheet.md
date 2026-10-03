# JS reverse cheat sheet — hooks, shims, task notes

Companion to `SKILL.md` (which teaches the five-phase method). Open this for the exact
snippets. Everything here runs against your own session on an in-scope target.

## DevTools console hooks (Capture phase)

Log every XHR and fetch call with URL, body, and stack:

```js
(() => {
  const _open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m, u) { this.__url = u; return _open.apply(this, arguments); };
  const _send = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function (body) {
    console.log('XHR', this.__url, body, new Error().stack);
    return _send.apply(this, arguments);
  };
  const _fetch = window.fetch;
  window.fetch = (...a) => { console.log('fetch', a[0], a[1]?.body, new Error().stack); return _fetch(...a); };
})();
```

Hook a suspected signing function once located (logs every input → output pair):

```js
const _orig = obj.sign;
obj.sign = (...a) => { const r = _orig(...a); console.log('sign in:', a, 'out:', r); return r; };
```

Catch where a request body is assembled:

```js
const _str = JSON.stringify;
JSON.stringify = function (v) { console.log('stringify', v); return _str.apply(this, arguments); };
```

## Global-search keywords (Observe phase)

`sign` · `signature` · `_signature` · `encrypt` · `decrypt` · `md5` · `sha1` / `sha256` ·
`hmac` · `CryptoJS` · `nonce` · `timestamp` · the exact param name from the request · the
request path fragment. Set `excludeMinified` only for a first pass — signers usually *live* in
minified bundles, so repeat the search with minified files included.

## Breakpoint defaults

- XHR/fetch breakpoint: use the shortest URL substring that still hits exactly the target
  endpoint.
- On pause, read frame 0 first, then walk up past framework frames (axios/fetch wrappers)
  into app code.
- Line/text breakpoints: only after hooks and XHR breakpoints proved insufficient
  (breakpoint-last principle).

## Node environment shims (Patch phase)

Starter set — add only as the first exception demands, one unit at a time:

```js
// Node >= 18: atob/btoa exist natively; older Node needs these
global.atob = (s) => Buffer.from(s, 'base64').toString('binary');
global.btoa = (s) => Buffer.from(s, 'binary').toString('base64');

global.window = globalThis;
global.self = globalThis;
global.navigator = { userAgent: '<UA from the captured request>', appName: 'Netscape', platform: 'Win32' };
global.location = { href: 'https://target.example/page', host: 'target.example', protocol: 'https:' };
global.document = {
  cookie: '<cookies from the session>',
  createElement: () => ({ style: {}, getContext: () => null, setAttribute() {}, getElementsByTagName: () => [] }),
  getElementById: () => null,
  addEventListener() {},
};

// Pin time/randomness to the captured sample for byte-identical comparison
Date.now = () => 1760000000000;          // value from the captured request's timestamp
Math.random = () => 0.123456789;
```

Patch order per failure: **plain value → function stub → object contract**. After each patch
re-run and confirm the first divergence moved forward; log every patch in `notes.md`.

## Task notes template (keep in `notes.md`)

```md
## Target request      <URL + which params are computed>
## Initiator lead      <script URL + stack frame>
## Suspicious scripts  <URLs>
## Capture             <hook/breakpoint used, hit location, key args/returns>
## Rebuild             <entry function, dependent scripts, env gaps>
## Patch log           <first divergence → shim applied → re-test result> (one line each)
## Output              <parameter reproduced? stable? remaining risk>
```

Minimum evidence to keep per task: a sample of the target request, the initiator stack, the
suspicious script URLs, key breakpoint locations, the function's real input/output pairs, the
first-divergence log, and every shim you added with its reason.
