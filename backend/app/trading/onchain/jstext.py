"""Read a JavaScript-built site the way a person sees it.

Lorenzo (29/09), after PFWA (pfwa.fun) was rejected as "site too weak
(21)": "Se il sito e' scritto in JavaScript non lo devi bocciare". Its
static HTML has no text at all, but the page a visitor sees is full: the
text travels inside the HTML as data for the JavaScript framework
(Next.js' `self.__next_f.push` chunks, `__NEXT_DATA__`, Nuxt, SvelteKit,
Astro islands, JSON-LD) and the browser builds the page from it.

Three steps, cheapest first:
- `extract`: pull the human text out of that data (no network, no browser);
- `render`: when the page is still an empty shell, open it in headless
  Chromium (Playwright) if the server has it; skipped silently otherwise;
- `is_shell`: what is still a shell after both is "unreadable", which the
  research pillar treats as unknown, never as a thin project.
"""
from __future__ import annotations

import asyncio
import contextvars
import html
import json
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

import httpx

from app.trading.onchain import egress

logger = logging.getLogger(__name__)

DEDUPE_WORDS = 4                  # shorter strings are fragments of a sentence, never dropped as repeats
SHELL_WORDS = 50                  # under this, a page with a JS app in it is a shell
RENDER_TIMEOUT_S = 20
RENDER_DAILY_MAX = 200
RENDER_ENV = "SITE_RENDER"        # "0" switches the headless browser off
# The Debian chromium package in the image (Dockerfile): Playwright's own
# download needs system libraries the slim image's Debian may not list.
CHROMIUM_ENV = "CHROMIUM_PATH"
RENDER_MAX_BYTES = 5_000_000       # one script or page handed to the browser
# httpx already decoded the body and sets its own length; the rest is per hop.
_HOP_HEADERS = {"content-encoding", "content-length", "transfer-encoding", "connection", "host"}

_NEXT_F = re.compile(r"self\.__next_f\.push\(\[1,(\"(?:[^\"\\]|\\.)*\")\]\)")
_JSON_SCRIPT = re.compile(
    r"<script\b([^>]*\b(?:type=[\"']application/(?:ld\+)?json[\"']|id=[\"']__NEXT_DATA__[\"'])[^>]*)>(.*?)</script>",
    re.S | re.I)
_INLINE_SCRIPT = re.compile(r"<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)
_ASTRO_PROPS = re.compile(r"<astro-island\b[^>]*\bprops=\"([^\"]*)\"", re.I)
_META = re.compile(r"<meta\b[^>]*>", re.I)
_ATTR = re.compile(r"([\w:-]+)\s*=\s*(\"[^\"]*\"|'[^']*')")
_NOSCRIPT = re.compile(r"<noscript[^>]*>(.*?)</noscript>", re.S | re.I)
_STRING = re.compile(r"\"((?:[^\"\\]|\\.)*)\"")
_T_ROW = re.compile(r"(?:^|\n)[0-9a-f]+:T([0-9a-f]+),")
_URL = re.compile(r"(https?://|www\.)\S+")
_JS_APP = re.compile(
    r"<div[^>]+id=[\"'](?:root|app|__next|__nuxt|svelte)[\"']|/_next/|__next_f|__NEXT_DATA__|__NUXT|"
    r"data-sveltekit|astro-island|<script[^>]+type=[\"']module[\"']|/assets/index-[\w-]+\.js|ng-version=", re.I)
# Values that are code or layout, never words for a reader.
_SKIP_KEYS = {"classname", "class", "href", "src", "srcset", "id", "rel", "as", "type", "crossorigin",
              "fetchpriority", "sizes", "media", "integrity", "nonce", "target", "name", "property",
              "charset", "httpequiv", "style", "d", "viewbox", "fill", "stroke", "xmlns", "strokewidth",
              "strokelinecap", "strokelinejoin", "buildid", "page", "assetprefix", "locale", "url",
              "image", "logo", "icon", "path", "slug", "key", "variant", "color", "font", "lang"}
# Next.js ships its not-found template inside every app-router page.
_BOILERPLATE = re.compile(r"^(404: )?this page could not be found\.?$", re.I)
_CODEY_TOKEN = re.compile(r"[:/=_\[\]#@$|\\]|^-|-\w*-|^[a-z]+[A-Z]\w*$|\.(js|css|png|svg|ico|woff2?)\b")
_CLASSY = re.compile(r"^[a-z0-9:\-\[\]/.%#!]+$")
_WORD = re.compile(r"^[A-Za-z][A-Za-z'’]*[.,:;!?]?$")


def _human(s: str, key: str | None = None, *, loose: bool = False) -> str:
    """The string as a reader would see it, or "" when it is code, a class
    list, a URL, a hash or a framework reference."""
    raw = s
    s = " ".join(s.split())
    if not s or (key or "").lower().replace("-", "") in _SKIP_KEYS or _BOILERPLATE.match(s):
        return ""
    if re.search(r"[{}<>]|=>|\bfunction\b|;\s*\w+\s*[=(]|\bvar\b|\bconst\b|[\w-]\(|,\"|\",", s):
        return ""
    bare = _URL.sub(" ", s).strip()
    toks = bare.split()
    if not toks:
        return ""
    chars = bare.replace(" ", "")
    if sum(c.isalpha() for c in chars) < 0.6 * len(chars):
        return ""
    if len(toks) == 1:
        # A lone word is text only when it sits in the page's children
        # ("Docs", "Overview") or is spaced as a fragment of a sentence.
        edge = raw != raw.strip()
        if not (_WORD.match(toks[0]) and (loose or key == "children" or edge) and len(toks[0]) >= 2):
            return ""
        return s
    if all(_CLASSY.match(t) for t in toks) and any("-" in t or ":" in t for t in toks):
        return ""
    codey = sum(1 for t in toks if _CODEY_TOKEN.search(t) or (len(t) >= 16 and re.search(r"\d", t)
                                                              and re.search(r"[a-z]", t)))
    if codey > 0.3 * len(toks):
        return ""
    return s


def _scan(payload: str, out: list[str]) -> None:
    """Every string literal of a JS/JSON payload that reads as text. A
    literal followed by ":" is a key; it names the value after it."""
    last_key, last_end = None, -1
    for m in _STRING.finditer(payload):
        after = payload[m.end():m.end() + 2].lstrip()
        try:
            value = json.loads(m.group(0))
        except ValueError:
            continue
        if after.startswith(":"):
            last_key, last_end = value, m.end()
            continue
        between = payload[last_end:m.start()] if last_end >= 0 else ""
        key = last_key if re.fullmatch(r"\s*:\s*\[?\s*", between) else None
        text = _human(value, key)
        if text:
            out.append(text)


def _walk(node, out: list[str], key: str | None = None) -> None:
    if isinstance(node, str):
        text = _human(node, key)
        if text:
            out.append(text)
    elif isinstance(node, dict):
        for k, v in node.items():
            _walk(v, out, str(k))
    elif isinstance(node, list):
        for v in node:
            _walk(v, out, key)


def _strip_tags(raw: str) -> str:
    body = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)).split())


def _next_flight(raw: str, out: list[str]) -> None:
    """Next.js app router: the React Server Components payload, pushed in
    JSON-escaped chunks. `id:T<hex>,` rows carry raw text of that many bytes
    (long markdown or HTML); the rest is JSON."""
    chunks = []
    for lit in _NEXT_F.findall(raw):
        try:
            chunks.append(json.loads(lit))
        except ValueError:
            continue
    if not chunks:
        return
    flight = "".join(chunks)
    rest, pos = [], 0
    for m in _T_ROW.finditer(flight):
        if m.start() < pos:
            continue
        size = int(m.group(1), 16)
        body = flight[m.end():].encode("utf-8")[:size].decode("utf-8", "ignore")
        rest.append(flight[pos:m.start()])
        text = _strip_tags(body)
        if text:
            out.append(text)
        pos = m.end() + len(body)
    rest.append(flight[pos:])
    _scan("\n".join(rest), out)


def _meta(raw: str, out: list[str]) -> None:
    for tag in _META.findall(raw):
        a = {k.lower(): html.unescape(v[1:-1]) for k, v in _ATTR.findall(tag)}
        which = (a.get("name") or a.get("property") or "").lower()
        if which in ("description", "og:description", "twitter:description", "og:title"):
            text = _human(a.get("content") or "", loose=True)
            if text:
                out.append(text)


def extract(raw: str) -> list[str]:
    """Human text a JS framework ships inside the HTML, in page order,
    without duplicates."""
    out: list[str] = []
    if not raw:
        return out
    _meta(raw, out)
    _next_flight(raw, out)
    for attrs, body in _JSON_SCRIPT.findall(raw):
        try:
            _walk(json.loads(html.unescape(body) if "&quot;" in body else body), out)
        except ValueError:
            _scan(body, out)
    for body in _INLINE_SCRIPT.findall(raw):
        if "__NUXT__" in body or "__sveltekit" in body:
            _scan(body, out)
    for props in _ASTRO_PROPS.findall(raw):
        try:
            _walk(json.loads(html.unescape(props)), out)
        except ValueError:
            continue
    for body in _NOSCRIPT.findall(raw):
        text = _strip_tags(body)
        if text:
            out.append(text)
    seen, unique = set(), []
    for t in out:
        k = t.lower()
        if k not in seen or len(t.split()) < DEDUPE_WORDS:
            seen.add(k)
            unique.append(t)
    return unique


def merge(static: str, extra: list[str]) -> str:
    """The static text, then what only the framework data had."""
    have = " ".join(static.split()).lower()
    add = []
    for t in extra:
        # Short fragments ("Robinhood Chain" inside a sentence) always stay:
        # dropping them would cut the sentence they belong to.
        if len(t.split()) < DEDUPE_WORDS or t.lower() not in have:
            add.append(t)
            have += " " + t.lower()
    return " ".join([static] + add).strip() if add else static


def beyond(text: str, seen: str) -> str:
    """`text` without the sentences `seen` already has: a JS-built docs page
    repeats the home page's header and footer, which would fill the excerpt
    the reader gets before any of the docs' own words."""
    have = " ".join((seen or "").split()).lower()
    parts = re.split(r"(?<=[.!?])\s+", " ".join((text or "").split()))
    return " ".join(p for p in parts if not (len(p.split()) >= 4 and p.lower() in have))


def links(raw: str) -> list[str]:
    """Links the framework data declares ("href":"/docs") and the static
    HTML does not show as <a> tags."""
    flight = []
    for lit in _NEXT_F.findall(raw or ""):
        try:
            flight.append(json.loads(lit))
        except ValueError:
            continue
    text = "".join(flight)
    for attrs, body in _JSON_SCRIPT.findall(raw or ""):
        text += body
    out = []
    for href in re.findall(r"\"href\"\s*:\s*\"([^\"]+)\"", text):
        if "/_next/" in href or re.search(r"\.(css|js|ico|png|jpe?g|svg|webp|woff2?)(\?|$)", href, re.I):
            continue
        if href not in out:
            out.append(href)
    return out


def is_shell(raw: str, words: int) -> bool:
    """A page whose text is built by JavaScript and which still shows next
    to nothing without running it."""
    return words < SHELL_WORDS and bool(_JS_APP.search(raw or ""))


# ------------------------------------------------------------ headless render

_sem: asyncio.Semaphore | None = None
_calls: dict[str, int] = {}
_unavailable = False          # no Playwright at all: nothing to retry
_down_until = 0.0             # the browser would not start: try again after a pause, never "off until restart"
DOWN_PAUSE_S = 900
CACHE_TTL_S = 6 * 3600
_cache: dict[str, tuple[float, str]] = {}
last_failure: dict[str, str] = {}   # url -> why it is still a shell, shown as a fact (AUREON, 08/10)
# A re-check someone asked for: it does not wait for tomorrow's quota.
URGENT: contextvars.ContextVar = contextvars.ContextVar("render_urgent", default=False)


def _failed(url: str, why: str) -> None:
    last_failure[url] = why
    while len(last_failure) > 500:
        last_failure.pop(next(iter(last_failure)))


def render_enabled() -> bool:
    return os.environ.get(RENDER_ENV, "1").strip().lower() not in ("0", "false", "no", "off")


async def render(url: str, allow_host: Callable[[str], Awaitable[bool]]) -> str | None:
    """The page's HTML after its JavaScript ran, or None when the server has
    no Playwright/Chromium, it is switched off, the daily cap is reached or
    the page does not load. One page at a time; every request the page makes
    goes through `allow_host`, so the browser cannot reach internal
    addresses either."""
    global _sem, _unavailable, _down_until
    if not render_enabled():
        _failed(url, "headless browser switched off")
        return None
    if _unavailable:
        _failed(url, "no headless browser on this server")
        return None
    if time.time() < _down_until:
        _failed(url, "headless browser did not start, retrying shortly")
        return None
    hit = _cache.get(url)
    if hit and time.time() - hit[0] < CACHE_TTL_S:
        return hit[1]
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        _unavailable = True
        _failed(url, "no headless browser on this server")
        return None
    today = time.strftime("%Y-%m-%d")
    if _calls.get(today, 0) >= RENDER_DAILY_MAX and not URGENT.get():
        _failed(url, "daily browser quota used")
        return None
    _sem = _sem or asyncio.Semaphore(1)
    async with _sem:
        if today not in _calls:
            _calls.clear()
        _calls[today] = _calls.get(today, 0) + 1
        hosts: dict[str, bool] = {}

        async def route(r):
            # A request still in flight when the page closes cannot be
            # answered any more: Playwright raised it from its event listener
            # ("handler is closed", 4 tracebacks in 30 minutes, 19/10).
            try:
                await _route(r)
            except Exception as exc:
                if "closed" not in str(exc).lower():
                    logger.warning("headless render: request not handled: %s", exc)

        async def _route(r):
            req = r.request
            if req.resource_type in ("image", "media", "font"):
                return await r.abort()
            if req.url.startswith(("data:", "blob:")):
                return await r.continue_()
            host = (urlparse(req.url).hostname or "").lower()
            if host not in hosts:
                hosts[host] = bool(host) and await allow_host(host)
            if not hosts[host]:
                return await r.abort()
            # The browser never connects by itself (its proxy is a dead
            # port): every request is fetched here, on a client that only
            # opens sockets to public IPs, and handed back to the page.
            try:
                # Redirects are followed here: a 3xx handed back to the page
                # sent Chromium to its dead proxy (hydrex.fi -> www, 30/09).
                resp = await net.request(req.method, req.url, content=req.post_data_buffer, follow_redirects=True,
                                         headers={k: v for k, v in req.headers.items()
                                                  if k.lower() not in _HOP_HEADERS})
            except httpx.HTTPError:
                return await r.abort()
            return await r.fulfill(status=resp.status_code, body=resp.content[:RENDER_MAX_BYTES],
                                   headers={k: v for k, v in resp.headers.items()
                                            if k.lower() not in _HOP_HEADERS})

        try:
            async with asyncio.timeout(RENDER_TIMEOUT_S + 10):
                async with async_playwright() as pw, egress.public_client(timeout=8.0) as net:
                    try:
                        # Docker gives /dev/shm 64 MB: Chromium's tabs crash on it
                        # without --disable-dev-shm-usage.
                        browser = await pw.chromium.launch(
                            headless=True, executable_path=os.environ.get(CHROMIUM_ENV) or None, proxy={"server": "http://127.0.0.1:9"},
                            args=["--proxy-bypass-list=<-loopback>", "--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"])
                    except Exception as exc:
                        # Was "unavailable until the next restart": one bad start
                        # left every JS site unreadable for days.
                        logger.warning("headless render: browser did not start: %s", exc)
                        _down_until = time.time() + DOWN_PAUSE_S
                        _failed(url, "headless browser did not start")
                        return None
                    try:
                        page = await browser.new_page(user_agent="Mozilla/5.0 (LiquidityEngine token check)")
                        await page.route("**/*", route)
                        await page.goto(url, wait_until="domcontentloaded", timeout=RENDER_TIMEOUT_S * 1000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=5000)
                        except Exception:
                            pass   # sockets that never go quiet: read what is there
                        built = await page.content()
                        _cache[url] = (time.time(), built)
                        for k in [k for k, (at, _) in _cache.items() if time.time() - at > CACHE_TTL_S]:
                            _cache.pop(k, None)
                        last_failure.pop(url, None)
                        return built
                    finally:
                        await browser.close()
        except Exception as exc:
            logger.warning("headless render of %s failed: %s", url, exc)
            _failed(url, f"page did not load in the browser ({type(exc).__name__})")
            return None
