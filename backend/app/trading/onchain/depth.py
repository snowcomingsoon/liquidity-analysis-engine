"""Analisi profonda di un progetto, per la classifica.

Lorenzo: "devi essere rigoroso [...] da GitHub E devi controllare i commit
[...] deve essere profonda sta cosa, la tokenomics non deve essere uno scam,
il sito deve essere fatto bene, magari se riesci ad analizzarne l'html e
vedere se e' fatto bene o se e' solo una pagina di presentazione ma dietro
non c'e' niente".

`legit.py` decide se un token si puo' proporre (passa / non passa). Qui si
misura QUANTO e' solido, su tre pilastri, ciascuno 0-100 con i numeri che
lo giustificano e i campanelli d'allarme:

- GitHub: gli ultimi 100 commit (cadenza, settimane attive, autori,
  quanti sono solo caricamenti dal browser), quanto codice c'e', test, CI,
  e se il repository e' nato insieme al token;
- sito: l'HTML, non solo il testo: pagine interne, documentazione e app
  raggiungibili davvero, sezioni (team, roadmap, tokenomics, audit),
  costruttori a modello, "lorem ipsum", eta' del dominio (RDAP);
- tokenomics: chi tiene i token, esclusi pool e locker (primo holder, primi
  10, creatore, insider), autorita' di mint e freeze, liquidita' bloccata,
  tasse.

Ogni pilastro puo' anche bocciare (`fatal`): un progetto con il creatore
che tiene l'80% dell'offerta non entra in classifica, qualunque sia il
resto. Tutte le funzioni `judge_*` sono pure: si provano senza rete.
"""
from __future__ import annotations

import logging
import math
import re
import time
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.trading.onchain import benchmark, jstext, legit, narratives

logger = logging.getLogger(__name__)

WEIGHTS = {"github": 0.40, "site": 0.30, "tokenomics": 0.30}

# GitHub
GH_COMMITS_PAGE = 100
GH_MIN_CODE_BYTES = 5_000          # sotto, e' un README con un file
GH_TRIVIAL_MAX = 0.70              # oltre, i commit sono solo caricamenti e ritocchi al README
GH_BORN_WITH_TOKEN_S = 3 * 86400
# I messaggi che GitHub scrive da solo quando si modifica un file dal browser.
_TRIVIAL = re.compile(
    r"^(initial commit|first commit|add files via upload|"
    r"(create|update|delete|rename|add) [\w./ -]+\.\w{1,6})$", re.I)
_TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "e2e"}

# Sito
SITE_FOLLOW = 3                    # pagine interne che si aprono davvero
SITE_MIN_WORDS_PAGE = 120          # una pagina interna "piena"
# The docs text the local reader weighs (it is popped, never stored; the AI
# readers cut their own prompt). 3000 chars left most of a docs page unread.
DOCS_EXCERPT_CHARS = 8000
_BUILDERS = ("wix", "carrd", "framer", "webflow", "squarespace", "wordpress", "zyro", "hostinger",
             "tilda", "weebly", "godaddy", "site123", "durable", "mobirise")
_FREE_HOSTS = ("carrd.co", "framer.website", "framer.ai", "webflow.io", "vercel.app", "netlify.app",
               "github.io", "wixsite.com", "pages.dev", "web.app", "firebaseapp.com", "gitbook.io",
               "notion.site", "replit.app", "lovable.app", "bolt.new")
_LOREM = re.compile(r"lorem ipsum|dolor sit amet|your (company|project) name", re.I)
# "Coming soon" is a placeholder only on a page with little else: a live
# product labels its next feature that way (HYDX, 30/09: 780 words, score 0).
_SOON = re.compile(r"coming soon", re.I)
SOON_MAX_WORDS = 150
_SECTIONS = {
    "team": re.compile(r"\b(team|founders?|about us|chi siamo|core contributors)\b", re.I),
    "roadmap": re.compile(r"\broad\s?map\b", re.I),
    "tokenomics": re.compile(r"\btoken\s?omics\b|\btoken distribution\b|\bsupply\b", re.I),
    "audit": re.compile(r"\baudit(ed|s)?\b|certik|hacken|halborn|ottersec|sec3|zellic", re.I),
}
_DOCS_HINT = re.compile(r"(^|[/.])(docs?|documentation|whitepaper|litepaper|gitbook|wiki|developers?|build|"
                        r"learn|guides?|research|laboratory|lab|spec|specification)([/.]|$)", re.I)
# A link to the project's contract on a block explorer: something is deployed.
_EXPLORER = re.compile(r"//[\w.-]*(?:scan|blockscout|explorer)[\w.-]*/(?:address|token|account|program)/\w{20,}", re.I)
_APP_HINT = re.compile(r"(^|[/.])(app|dapp|dashboard|launch|platform|beta)([/.]|$)", re.I)
_APP_TEXT = re.compile(r"\b(launch app|open app|enter app|go to app|use app|try (it|now)|dashboard)\b", re.I)
RDAP = "https://rdap.org/domain/{domain}"

# Tokenomics
TOP1_MAX_PCT = 20.0
TOP10_MAX_PCT = 60.0
CREATOR_MAX_PCT = 15.0
TAX_MAX_PCT = 5.0
_POOLISH = {"AMM", "LOCKER", "BURN"}
_DEAD = {"0x000000000000000000000000000000000000dead", "0x0000000000000000000000000000000000000000"}


def _pillar(key: str, score: float | None, facts: dict, flags: list[str], fatal: str = "") -> dict:
    return {"key": key, "score": None if score is None else int(max(0, min(100, round(score)))),
            "facts": facts, "flags": flags, "fatal": fatal}


def missing_github(why: str, **facts) -> dict:
    """No public code of the project's own. Not a defect: many serious
    projects keep it private (Lorenzo, 25/09: "non tutti hanno il github
    pubblico, e' importante ma non deve evitare di scegliere progetti che
    sul resto sono comunque legit"). The pillar has no score, the others
    carry the weight, and the leaderboard asks more of them."""
    return {"key": "github", "score": None, "facts": {"missing": True, **facts}, "flags": [why], "fatal": ""}


def _pending(key: str, why: str) -> dict:
    """Il dato non c'e' ancora (API giu', token troppo nuovo): si riprova."""
    return {"key": key, "score": None, "facts": {}, "flags": [], "fatal": "", "pending": why}


UNREADABLE_JS = "site built in JavaScript, not readable"


def _unreadable(key: str, why: str, facts: dict | None = None) -> dict:
    """We could not read the page (a JavaScript shell nothing could open):
    unknown, not weak. No score; the research pillar and the leaderboard
    treat it like a pending pillar, never as a thin project (Lorenzo, 29/09:
    "Se il sito e' scritto in JavaScript non lo devi bocciare")."""
    return {"key": key, "score": None, "facts": {**(facts or {}), "unreadable": why}, "flags": [why],
            "fatal": "", "unreadable": why}


def _ts(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# ------------------------------------------------------------------ GitHub

async def fetch_github(full_name: str, client: httpx.AsyncClient) -> dict | None:
    """Repo, ultimi 100 commit, contributori, linguaggi, cartella principale.
    None = GitHub non risponde (limite di richieste): si riprova."""
    base = f"{legit.GITHUB_API}/repos/{full_name}"
    h = legit._gh_headers()
    try:
        repo = await legit.gh_get(client, base, headers=h, timeout=8.0)
        if repo.status_code == 404:
            return {}
        if repo.status_code != 200:
            return None
        out = {"repo": repo.json()}
        for key, url, params in (("commits", f"{base}/commits", {"per_page": GH_COMMITS_PAGE}),
                                 ("contributors", f"{base}/contributors", {"per_page": 30, "anon": 1}),
                                 ("languages", f"{base}/languages", None),
                                 ("root", f"{base}/contents", None),
                                 ("participation", f"{base}/stats/participation", None)):
            r = await legit.gh_get(client, url, params=params, headers=h, timeout=8.0)
            if key == "participation" and r.status_code != 200:
                out[key] = {}   # 202: GitHub la sta ancora calcolando; si usano i 100 commit
            elif r.status_code in (204, 404, 409):  # vuoto, o niente contributori calcolati
                out[key] = [] if key != "languages" else {}
            elif r.status_code == 200:
                out[key] = r.json()
            else:
                return None
        return out
    except (httpx.HTTPError, ValueError):
        return None


def judge_github(data: dict | None, launched_at: float | None = None, now: float | None = None) -> dict:
    if data is None:
        return _pending("github", "GitHub not responding")
    if not data or not data.get("repo"):
        return _pillar("github", 0, {}, [], "GitHub link without a repository")
    now = now or time.time()
    repo, commits = data["repo"], [c for c in data.get("commits") or [] if isinstance(c, dict)]
    name = repo.get("full_name") or "?"
    if repo.get("fork"):
        return _pillar("github", 0, {"repo": name}, [], f"{name} is a fork")

    dates = [t for t in (_ts(((c.get("commit") or {}).get("author") or {}).get("date")) for c in commits) if t]
    messages = [((c.get("commit") or {}).get("message") or "").strip().splitlines()[0:1] for c in commits]
    trivial = sum(1 for m in messages if not m or _TRIVIAL.match(m[0]))
    authors = {(c.get("author") or {}).get("login") or ((c.get("commit") or {}).get("author") or {}).get("email")
               for c in commits} - {None, ""}
    people = [x for x in data.get("contributors") or [] if isinstance(x, dict)]
    contributors = len(people)
    # La somma dei contributi dei primi 30: la storia intera, non solo gli ultimi 100 commit.
    total_commits = max(sum(int(x.get("contributions") or 0) for x in people), len(commits))
    languages = data.get("languages") or {}
    code = sum(v for v in languages.values() if isinstance(v, (int, float)))
    names = {(x.get("name") or "").lower() for x in data.get("root") or [] if isinstance(x, dict)}
    has_tests = bool(names & _TEST_DIRS) or any(n.startswith(("test_", "jest.config", "vitest.config",
                                                                "pytest.ini", "foundry.toml", "hardhat.config"))
                                                for n in names)
    has_ci = ".github" in names or ".gitlab-ci.yml" in names or ".circleci" in names
    has_readme = any(n.startswith("readme") for n in names)
    days = {time.strftime("%Y-%m-%d", time.gmtime(t)) for t in dates}
    weekly = [w for w in ((data.get("participation") or {}).get("all") or []) if isinstance(w, int)]
    if len(weekly) >= 13:
        # Le 52 settimane intere: i 100 commit di un repo molto attivo coprono pochi giorni.
        weeks12 = {i for i, n in enumerate(reversed(weekly[-12:])) if n}
        commits90 = sum(weekly[-13:])
    else:
        weeks12 = {int((now - t) // (7 * 86400)) for t in dates if now - t < 84 * 86400}
        commits90 = sum(1 for t in dates if now - t < 90 * 86400)
    last_days = (now - max(dates)) / 86400 if dates else None
    span_days = (max(dates) - min(dates)) / 86400 if dates else 0
    created = _ts(repo.get("created_at"))
    trivial_ratio = trivial / len(commits) if commits else 1.0
    top_langs = [k for k, _ in sorted(languages.items(), key=lambda kv: -kv[1])[:3]]

    facts = {
        "repo": name, "url": repo.get("html_url"), "description": (repo.get("description") or "")[:160],
        "commits": f"{len(commits)}+" if len(commits) >= GH_COMMITS_PAGE else len(commits),
        "commits_90d": commits90, "active_days": len(days), "active_weeks_12": len(weeks12),
        "span_days": round(span_days), "last_commit_days": None if last_days is None else round(last_days, 1),
        "authors": len(authors), "contributors": contributors, "code_kb": round(code / 1024),
        "languages": top_langs, "tests": has_tests, "ci": has_ci, "readme": has_readme,
        "license": ((repo.get("license") or {}).get("spdx_id")) or None,
        "stars": repo.get("stargazers_count") or 0, "forks": repo.get("forks_count") or 0,
        "trivial_pct": round(trivial_ratio * 100), "created_at": repo.get("created_at"),
        # Per il confronto con DREGG (benchmark.py).
        "languages_all": list(languages), "topics": (repo.get("topics") or [])[:12],
        "root_dirs": sorted(x.get("name") for x in data.get("root") or []
                            if isinstance(x, dict) and x.get("type") == "dir" and x.get("name")),
        "total_commits": total_commits,
    }
    flags: list[str] = []
    fatal = ""
    if not commits:
        fatal = "empty repository"
    elif code < GH_MIN_CODE_BYTES:
        fatal = f"almost no code ({code // 1024} KB)"
    elif len(days) < 2:
        fatal = "all commits on a single day"
    elif trivial_ratio > GH_TRIVIAL_MAX:
        fatal = f"{round(trivial_ratio * 100)}% of commits are uploads or README tweaks"
    if launched_at and created and 0 <= launched_at - created < GH_BORN_WITH_TOKEN_S and span_days < 3:
        flags.append("repository born with the token")
    if last_days is not None and last_days > 90:
        flags.append(f"idle for {round(last_days)} days")
    if len(authors) <= 1 and contributors <= 1:
        flags.append("single author")
    if trivial_ratio > 0.4 and not fatal:
        flags.append(f"{round(trivial_ratio * 100)}% trivial commits")
    if fatal:
        return _pillar("github", 0, facts, flags, fatal)

    recency = 0 if last_days is None else 10 if last_days <= 7 else 6 if last_days <= 30 else 3 if last_days <= 90 else 0
    score = (min(commits90, 60) / 60 * 25                       # attivita'
             + min(len(weeks12), 12) / 12 * 20                  # costanza
             + min(max(len(authors), contributors), 5) / 5 * 15 # squadra
             + min(max(math.log10(max(code, 1)) - 4, 0) / 2, 1) * 15  # codice: 10 KB -> 0, 1 MB -> pieno
             + 6 * has_tests + 5 * has_ci + 2 * has_readme + 2 * bool(facts["license"])
             + recency)
    score *= 1 - 0.5 * trivial_ratio
    if "repository born with the token" in flags:
        score *= 0.8
    return _pillar("github", score, facts, flags)


async def analyze_github(urls: list[str], client: httpx.AsyncClient, launched_at: float | None,
                         token: dict | None = None, website: str | None = None) -> dict:
    targets = legit.github_targets(urls)
    if not targets:
        return missing_github("no public GitHub")
    # Every linked repository is tried, named ones first: one dead or
    # private link (BV7X, 29/09) is not proof the project has no code.
    # Then the linking accounts themselves: BV7X links two private repos,
    # its account keeps a public one.
    owners = [(o, None) for o in dict.fromkeys(o for o, r in targets if r) if (o, None) not in targets]
    repo: dict | None = {}
    for owner, name in [*sorted(targets, key=lambda t: t[1] is None), *owners]:
        try:
            repo = await legit.github_repo(owner, name, client)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            repo = None
        if repo is None:
            return _pending("github", "GitHub not responding")
        if repo:
            break
    if not repo:
        # Private or deleted repositories: code we cannot see, not a fake link.
        return missing_github("linked GitHub repositories are private or deleted",
                              linked=[f"{o}/{r}" if r else o for o, r in targets])
    # Un link a una libreria o a una piattaforma non e' il codice del progetto.
    # github_verified: the README names the token's address, proof enough.
    if token and not token.get("github_verified") \
            and not benchmark.is_benchmark(token.get("chain"), token.get("token_address")) \
            and not legit.github_belongs(repo, token, website):
        return missing_github("linked GitHub is not the project's own", repo=repo.get("full_name"))
    return judge_github(await fetch_github(repo["full_name"], client), launched_at)


# -------------------------------------------------------------------- sito

class _Anatomy(HTMLParser):
    """Quello che serve dell'HTML, senza dipendenze: link, titoli, meta,
    script, moduli."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []   # (href, testo)
        self.headings = 0
        self.scripts = 0
        self.forms = 0
        self.nav = False
        self.meta: dict[str, str] = {}
        self.icon = False
        self.root_div = False
        self._a: str | None = None
        self._a_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "a" and a.get("href"):
            self._a, self._a_text = a["href"], []
        elif tag in ("h1", "h2", "h3"):
            self.headings += 1
        elif tag == "script":
            self.scripts += 1
        elif tag == "form":
            self.forms += 1
        elif tag == "nav":
            self.nav = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link" and "icon" in a.get("rel", "").lower():
            self.icon = True
        elif tag == "div" and a.get("id") in ("root", "app", "__next", "__nuxt", "svelte"):
            self.root_div = True

    def handle_data(self, data):
        if self._a is not None:
            self._a_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._a is not None:
            self.links.append((self._a, " ".join("".join(self._a_text).split())[:80]))
            self._a = None


def _site_root(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def anatomy(html_text: str, base_url: str) -> dict:
    """Cosa c'e' nella pagina: pagine interne, documentazione, app, sezioni."""
    p = _Anatomy()
    try:
        p.feed(html_text)
    except Exception:  # HTML rotto: si tiene quello che si e' letto
        pass
    host = (urlparse(base_url).hostname or "").lower()
    root = _site_root(host.removeprefix("www."))
    internal, docs, app, github, explorer = [], [], [], [], []
    anchors = {h for h, _ in p.links}
    # A JS-built page declares its links in the framework data, not in <a>.
    p.links += [(h, "") for h in jstext.links(html_text) if h not in anchors]
    for href, text in p.links:
        url = urljoin(base_url, href.strip())
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            continue
        h = u.hostname.lower()
        target = (h + u.path.rstrip("/")).lower()
        if "github.com" in h:
            github.append(url)
        if _EXPLORER.search(url):
            explorer.append(url)
        same = h == host or h.endswith("." + root) or h == root
        if _DOCS_HINT.search(target) and url not in docs:
            docs.append(url)
        elif same and (_APP_HINT.search(target) or _APP_TEXT.search(text)) and url not in app:
            app.append(url)
        if same and (h != host or u.path.rstrip("/") not in ("", urlparse(base_url).path.rstrip("/"))):
            key = h + u.path.rstrip("/")
            if key not in [x[0] for x in internal]:
                internal.append((key, url))
    _, text = legit.page_text(html_text)
    generator = p.meta.get("generator", "").lower()
    builder = next((b for b in _BUILDERS if b in generator or f"{b}." in html_text[:20000].lower()), None)
    return {
        "words": len(text.split()),
        "text": text,
        "internal": [u for _, u in internal],
        "docs": docs, "app": app, "github": github, "explorer": explorer,
        "sections": sorted(k for k, rx in _SECTIONS.items() if rx.search(text)),
        "headings": p.headings, "scripts": p.scripts, "forms": p.forms, "nav": p.nav,
        "meta_description": bool(p.meta.get("description") or p.meta.get("og:description")),
        "og_image": bool(p.meta.get("og:image") or p.meta.get("twitter:image")),
        "icon": p.icon,
        "spa": p.root_div and p.scripts > 0,
        "builder": builder,
        "free_host": next((f for f in _FREE_HOSTS if host == f or host.endswith("." + f)), None),
        "lorem": bool(_LOREM.search(text)) or (bool(_SOON.search(text)) and len(text.split()) < SOON_MAX_WORDS),
    }


# Siti che esistono a prescindere dal token: un link li' non dice niente del progetto.
_GENERIC = ("wikipedia.org", "google.com", "apple.com", "amazon.com", "reddit.com", "facebook.com",
            "coingecko.com", "coinmarketcap.com", "solscan.io", "etherscan.io", "pump.fun", "jup.ag",
            "raydium.io", "binance.com", "archive.org", "imgur.com", "ipfs.io")


def _not_own(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    return next((g for g in _GENERIC if host == g or host.endswith("." + g)), None)


def _registration(rdap: dict | None) -> float | None:
    for ev in (rdap or {}).get("events") or []:
        if ev.get("eventAction") == "registration":
            return _ts(ev.get("eventDate"))
    return None


def judge_site(page: dict | None, followed: list[dict], registered_at: float | None,
               token_address: str = "", launched_at: float | None = None, now: float | None = None) -> dict:
    """page: esito di `anatomy` + url/https; followed: le pagine interne
    aperte davvero, ognuna {kind: docs|app|page, ok, words}."""
    if page is None:
        return _pending("site", "website unreachable")
    now = now or time.time()
    docs_ok = any(f["ok"] and f["kind"] == "docs" and f["words"] >= SITE_MIN_WORDS_PAGE for f in followed)
    app_ok = any(f["ok"] and f["kind"] == "app" for f in followed)
    pages_ok = sum(1 for f in followed if f["ok"] and f["words"] >= SITE_MIN_WORDS_PAGE)
    domain_days = (now - registered_at) / 86400 if registered_at else None
    before_launch = (launched_at - registered_at) / 86400 if registered_at and launched_at else None
    cites = bool(token_address) and token_address.lower() in (page.get("text") or "").lower()
    facts = {
        "url": page.get("url"), "words": page["words"], "internal_pages": len(page["internal"]),
        "pages_ok": pages_ok, "docs": bool(page["docs"]), "docs_ok": docs_ok,
        "app": bool(page["app"]), "app_ok": app_ok, "sections": page["sections"],
        "contract_link": bool(page.get("explorer")),
        "builder": page["builder"], "free_host": page["free_host"], "spa": page["spa"],
        "domain_days": None if domain_days is None else round(domain_days),
        "cites_contract": cites, "https": bool(page.get("https")),
        "tech_terms": benchmark.site_terms(page.get("text") or ""),
        "narratives": narratives.match(page.get("text") or ""),
    }
    flags: list[str] = []
    if page.get("not_own"):
        return _pillar("site", 0, facts, flags, f"not the project's website ({page['not_own']})")
    if page.get("shell") and not pages_ok:
        return _unreadable("site", UNREADABLE_JS, facts)
    if page["lorem"]:
        return _pillar("site", 0, facts, flags, "placeholder text (lorem ipsum / coming soon)")
    empty = page["words"] < 40 and not page["internal"] and not page["spa"]
    if empty:
        return _pillar("site", 0, facts, flags, "empty page")
    if not page["internal"] and not page["docs"] and not page["app"]:
        flags.append("single page, nothing behind it")
    if page["builder"]:
        flags.append(f"built with {page['builder']}")
    if page["free_host"]:
        flags.append(f"on a free domain ({page['free_host']})")
    # "Registered with the token" is how most new projects start: not a flag
    # (29/09, PFWA judged 22 on it). A site younger than its token still is.
    if before_launch is not None and before_launch < -1:
        flags.append("domain younger than the token")
    if page["spa"] and page["words"] < 80:
        flags.append("content rendered via JavaScript")

    domain = (0 if domain_days is None else 13 if domain_days >= 180 else 8 if domain_days >= 30
              else 4 if domain_days >= 7 else 0)
    score = (min(page["words"], 1500) / 1500 * 18
             + min(len(page["internal"]), 8) / 8 * 12 + min(pages_ok, SITE_FOLLOW) / SITE_FOLLOW * 8
             + (15 if docs_ok else 7 if page["docs"] else 0)
             + (15 if app_ok else 7 if page["app"] else 0)
             + 3 * len(page["sections"])
             + domain
             + 2 * bool(page.get("https")) + 2 * page["meta_description"] + 2 * page["og_image"]
             + 1 * page["icon"] + 2 * cites)
    if page["free_host"]:
        score -= 10
    if page["builder"]:
        score -= 4
    return _pillar("site", score, facts, flags)


async def analyze_site(url: str | None, client: httpx.AsyncClient, token_address: str = "",
                       launched_at: float | None = None) -> tuple[dict, list[str]]:
    """(pilastro, link a GitHub trovati nell'HTML)."""
    if not url:
        return _pillar("site", 0, {}, [], "no own website"), []
    site = await legit.fetch_site(url, client)
    if not site.get("ok"):
        return _pending("site", site.get("error") or "website unreachable"), []
    page = anatomy(site.get("html") or "", site["final_url"])
    page.update(url=site["final_url"], https=site["final_url"].startswith("https://"),
                not_own=_not_own(site["final_url"]), shell=bool(site.get("shell")))
    followed: list[dict] = []
    docs_text = ""
    todo = ([("docs", u) for u in page["docs"][:1]] + [("app", u) for u in page["app"][:1]]
            + [("page", u) for u in page["internal"] if u not in page["docs"][:1] + page["app"][:1]])
    for kind, u in todo[:SITE_FOLLOW]:
        sub = await legit.fetch_site(u, client)
        followed.append({"kind": kind, "ok": bool(sub.get("ok")),
                         "words": len((sub.get("text") or "").split())})
        if kind == "docs" and sub.get("ok"):
            docs_text = jstext.beyond(sub.get("text") or "", page.get("text") or "")[:DOCS_EXCERPT_CHARS]
    registered = None
    host = (urlparse(site["final_url"]).hostname or "").removeprefix("www.")
    if host and not page["free_host"]:
        try:
            r = await client.get(RDAP.format(domain=_site_root(host)), timeout=8.0, follow_redirects=True)
            registered = _registration(r.json()) if r.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            registered = None
    pillar = judge_site(page, followed, registered, token_address, launched_at)
    pillar["facts"]["rendered"] = bool(site.get("rendered"))
    if site.get("render_error"):
        pillar["facts"]["render_error"] = site["render_error"]   # why it stayed a shell, not a guess
    pillar.setdefault("facts", {})["excerpt"] = re.sub(r"\s+", " ", page.get("text") or "")[:1500]
    pillar["facts"]["docs_excerpt"] = docs_text
    return pillar, page["github"]


# -------------------------------------------------------------- tokenomics

async def rugcheck_report(mint: str, client: httpx.AsyncClient) -> dict | None:
    try:
        r = await client.get(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report", timeout=12.0)
    except httpx.HTTPError:
        return None
    return r.json() if r.status_code == 200 else None


def judge_tokenomics_solana(report: dict | None, exclude: set[str] | None = None,
                            verified: dict | None = None) -> dict:
    """Dal report completo di RugCheck. `exclude`: conti che non sono
    persone (curva di pump.fun, pool) oltre a quelli che RugCheck conosce.
    `verified`: linked.verify, the linked wallets read on-chain (Top 50)."""
    if not report or not report.get("topHolders") and not report.get("token"):
        return _pending("tokenomics", "RugCheck does not have the token yet")
    known = report.get("knownAccounts") or {}
    skip = set(exclude or ()) | {a for a, v in known.items() if (v or {}).get("type") in _POOLISH}
    for m in report.get("markets") or []:
        skip |= {v for v in (m.get("pubkey"), m.get("liquidityA"), m.get("liquidityB"),
                             (m.get("liquidityAAccount") or {}).get("owner"),
                             (m.get("liquidityBAccount") or {}).get("owner")) if isinstance(v, str)}
    holders = [h for h in report.get("topHolders") or []
               if h.get("address") not in skip and h.get("owner") not in skip]
    # Accounts owned by a program (off-curve owner: staking, vesting, locks
    # RugCheck does not name, treasuries) are not "a single wallet": out of
    # the wallet limits like EVM contracts (Lorenzo, 19/10), with the same
    # cap on the biggest one and the same penalty.
    programs = sorted((float(h.get("pct") or 0) for h in holders if legit.is_program_account(h.get("owner"))),
                      reverse=True)
    all_pcts = sorted((float(h.get("pct") or 0) for h in holders), reverse=True)
    pcts = sorted((float(h.get("pct") or 0) for h in holders if not legit.is_program_account(h.get("owner"))),
                  reverse=True)
    supply = float((report.get("token") or {}).get("supply") or 0)
    creator_pct = float(report.get("creatorBalance") or 0) / supply * 100 if supply else 0.0
    insiders = sum(1 for h in holders if h.get("insider")) + int(report.get("graphInsidersDetected") or 0)
    # The wallet count alone misleads: one airdrop of dust makes hundreds of
    # "linked" wallets holding nothing (DREGG 30/09: 761 of 807 held 744 tokens each).
    linked_pct, _ = legit.linked_share(report) if report.get("insiderNetworks") else (None, 0)
    if verified:
        linked_pct, insiders = verified["pct"], verified["wallets"]
    lp_locked = max((float((m.get("lp") or {}).get("lpLockedPct") or 0) for m in report.get("markets") or []),
                    default=None)
    fee = float((report.get("transferFee") or {}).get("pct") or 0)
    out = _judge_tokenomics(
        top1=pcts[0] if pcts else 0.0, top10=sum(pcts[:10]), creator=creator_pct,
        holders=int(report.get("totalHolders") or 0), insiders=insiders, linked_pct=linked_pct,
        linked_verified=verified, lp_locked=lp_locked,
        mintable=bool(report.get("mintAuthority")), freezable=bool(report.get("freezeAuthority")),
        tax=fee, rugged=bool(report.get("rugged")),
        # null = revoked (a real answer); a missing key = RugCheck didn't say.
        unknown=frozenset(k for k, present in (
            ("split", bool(report.get("topHolders"))),
            ("mint", "mintAuthority" in report),
            ("freeze", "freezeAuthority" in report),
        ) if not present))
    return _with_contracts(out, sum(programs), programs[0] if programs else 0.0, sum(all_pcts[:10]),
                           "one program account holds", "held by programs (staking, vesting, locks or treasury)")


def _with_contracts(out: dict, in_contracts: float, biggest: float, top10_all: float,
                    fatal_text: str, flag_text: str) -> dict:
    """The holders left out of the wallet limits (EVM contracts, Solana
    program accounts): in the facts, a cap on the biggest one, a penalty."""
    out["facts"]["contracts_pct"] = round(in_contracts, 1)
    out["facts"]["top10_all_pct"] = round(top10_all, 1)
    # A contract is not proof of a pool or a vesting: a multisig or a proxy
    # the team controls is a whale too (audit 29/09, M01). Unidentified
    # contracts stay out of the per-wallet limits (GRID, BV7X), but one
    # holding a majority of the supply is not waved through.
    if biggest > CONTRACT_MAX_PCT and not out["fatal"]:
        out["fatal"] = f"{fatal_text} {biggest:.0f}%"
        out["score"] = 0
    if in_contracts > TOP1_MAX_PCT and not out["fatal"]:
        out["flags"].append(f"{in_contracts:.0f}% {flag_text}")
        out["score"] = max(0, out["score"] - round(min(in_contracts, 60) / 6))
    return out


LP_COVER_MIN = 0.5


def judge_tokenomics_evm(info: dict | None, pair_address: str = "", liquidity_usd: float = 0.0) -> dict:
    """Da GoPlus (Robinhood Chain): holders con percentuale 0-1."""
    if not info:
        return _pending("tokenomics", "GoPlus does not have the token yet")

    def pct(v) -> float:
        try:
            return float(v or 0) * 100
        except (TypeError, ValueError):
            return 0.0

    # The pools GoPlus lists are pools, not holders: Uniswap v4 keeps every
    # pool's tokens in its PoolManager (HYDX, 30/09: 9% of the supply).
    pools = {pair_address.lower()} | {str(d.get(k) or "").lower() for d in info.get("dex") or []
                                      for k in ("pair", "pool_manager")} - {""}
    holders = [h for h in info.get("holders") or []
               if (h.get("address") or "").lower() not in _DEAD | pools
               and not str(h.get("is_locked")) == "1"
               and not re.search(r"pool|pair|lp|lock|burn", h.get("tag") or "", re.I)]
    # A contract is not "a single wallet": GoPlus leaves Robinhood's pools
    # (Uniswap v4 keeps every pool in one PoolManager), vesting and launchpad
    # contracts untagged, and they failed serious projects (29/09: GRID 29%,
    # BV7X 41%, both contracts). They leave the concentration limits, stay
    # in the facts and cost points (Lorenzo: "se non passano le nostre regole
    # sono da rivedere [...] risultano troppo severi").
    contracts = [h for h in holders if str(h.get("is_contract")) == "1"]
    in_contracts = sum(pct(h.get("percent")) for h in contracts)
    biggest_contract = max((pct(h.get("percent")) for h in contracts), default=0.0)
    unknown = frozenset(k for k, present in (
        ("split", bool(info.get("holders"))),
        ("mint", "is_mintable" in info),
        ("freeze", "transfer_pausable" in info),
        ("tax", "buy_tax" in info or "sell_tax" in info),
    ) if not present)
    pcts = sorted((pct(h.get("percent")) for h in holders if h not in contracts), reverse=True)
    lps = info.get("lp_holders") or []
    lp_locked = sum(pct(h.get("percent")) for h in lps
                    if str(h.get("is_locked")) == "1" or (h.get("address") or "").lower() in _DEAD) if lps else None
    # GoPlus lists the LP positions of the pools it knows: on HYDX (30/09)
    # $595 of positions in a small Uniswap v4 pool, while the pool that
    # trades held $63k. A lock share of a pool that is not the market is no
    # reading of the market: left out, with a note.
    lp_value = 0.0
    for h in lps:
        try:
            lp_value += float(h.get("value") or 0)
        except (TypeError, ValueError):
            pass
    lp_note = ""
    valued = any(h.get("value") not in (None, "") for h in lps)    # v4 positions carry a USD value
    if lp_locked is not None and valued and liquidity_usd > 0 and lp_value < LP_COVER_MIN * liquidity_usd:
        lp_locked = None
        lp_note = (f"GoPlus LP data covers ${lp_value:,.0f} of ${liquidity_usd:,.0f} liquidity: "
                   "the main pool's lock is not in it")
    out = _judge_tokenomics(
        top1=pcts[0] if pcts else 0.0, top10=sum(pcts[:10]),
        creator=max(pct(info.get("creator_percent")), pct(info.get("owner_percent"))),
        holders=int(info.get("holder_count") or 0), insiders=0, lp_locked=lp_locked,
        mintable=str(info.get("is_mintable")) == "1", freezable=str(info.get("transfer_pausable")) == "1",
        tax=max(pct(info.get("buy_tax")), pct(info.get("sell_tax"))),
        rugged=str(info.get("is_honeypot")) == "1", unknown=unknown)
    if lp_note:
        out["facts"]["lp_note"] = lp_note
    out["facts"]["top_holders"] = [
        {"pct": round(pct(h.get("percent")), 2), "contract": str(h.get("is_contract")) == "1",
         **({"tag": h["tag"]} if h.get("tag") else {})}
        for h in sorted(holders, key=lambda h: -pct(h.get("percent")))[:10]]
    top10_all = sum(sorted((pct(h.get("percent")) for h in holders), reverse=True)[:10])
    return _with_contracts(out, in_contracts, biggest_contract, top10_all,
                           "one unidentified contract holds", "held by contracts (pools, vesting or treasury)")


CONTRACT_MAX_PCT = 50.0

GECKO_TOKENOMICS_BASE = 50
GECKO_TOKENOMICS_MAX = 65


def judge_tokenomics_gecko(info: dict | None) -> dict:
    """Fallback when GoPlus has no data (new Robinhood tokens, 29/09: AUREON,
    PFWA, GRID): holder count and split from GeckoTerminal's token info.
    Informational only. Its top 10 counts pools and contracts (PoolManager,
    vesting, launchpad), so it must not drive the top1/top10 fatal limits,
    and with no mint/freeze/tax/LP reading the score stays modest: a neutral
    50 plus the same log-scale holder component as _judge_tokenomics, capped
    at 65 so it never beats a real GoPlus reading of a sound token."""
    info = info or {}
    try:
        holders = int(info.get("holders") or 0)
    except (TypeError, ValueError):
        holders = 0
    split = info.get("holders_split") or {}
    try:
        top10 = float(split.get("top_10")) if split.get("top_10") not in (None, "") else None
    except (TypeError, ValueError):
        top10 = None
    if not holders and top10 is None:
        return _pending("tokenomics", "GoPlus does not have the token yet")
    facts = {"holders": holders, "source": "geckoterminal",
             **({"gecko_top10_pct": round(top10, 1)} if top10 is not None else {})}
    score = GECKO_TOKENOMICS_BASE + min(max(math.log10(max(holders, 1)) - 1.7, 0) / 2, 1) * 15
    return _pillar("tokenomics", min(score, GECKO_TOKENOMICS_MAX), facts,
                   ["holder split from GeckoTerminal (pools included)"])


def _judge_tokenomics(*, top1: float, top10: float, creator: float, holders: int, insiders: int,
                      lp_locked: float | None, mintable: bool, freezable: bool, tax: float,
                      rugged: bool, unknown: frozenset[str] = frozenset(),
                      linked_pct: float | None = None, linked_verified: dict | None = None) -> dict:
    """unknown: the checks the source did not answer ("split", "mint",
    "freeze", "tax", "lp"). A missing answer is not a passed check (audit
    29/09, M02): it earns no points and is listed in the flags."""
    facts = {"top1_pct": round(top1, 1), "top10_pct": round(top10, 1), "creator_pct": round(creator, 1),
             "holders": holders, "insiders": insiders,
             "linked_pct": None if linked_pct is None else round(linked_pct, 1),
             "linked_verified": linked_verified,
             "lp_locked_pct": None if lp_locked is None else round(min(lp_locked, 100), 1),
             "mint": mintable, "freeze": freezable, "tax_pct": round(tax, 1)}
    fatal = ("already rugged or honeypot" if rugged
             else "new tokens can be minted (mint enabled)" if mintable
             else "accounts can be frozen (freeze enabled)" if freezable
             else f"creator holds {creator:.0f}%" if creator > CREATOR_MAX_PCT
             else f"a single wallet holds {top1:.0f}%" if top1 > TOP1_MAX_PCT
             else f"top 10 hold {top10:.0f}%" if top10 > TOP10_MAX_PCT
             else f"{tax:.0f}% tax" if tax > TAX_MAX_PCT
             else "")
    flags = []
    if linked_pct is not None:
        if linked_pct >= 1:
            flags.append(f"linked wallets hold {linked_pct:.0f}% of supply ({insiders} wallets"
                         + (", balances checked on-chain, airdrop links ignored)" if linked_verified else ")"))
    elif insiders:
        flags.append(f"{insiders} wallets linked to each other")
    if lp_locked is not None and lp_locked < 80:
        flags.append(f"only {lp_locked:.0f}% of liquidity locked")
    if creator > 5:
        flags.append(f"creator at {creator:.0f}%")
    if unknown:
        flags.append("not verified: " + ", ".join(sorted(unknown)))
        facts["unverified"] = sorted(unknown)
    if fatal:
        return _pillar("tokenomics", 0, facts, flags, fatal)
    score = ((0 if "split" in unknown else max(0.0, min(1.0, (TOP10_MAX_PCT - top10) / (TOP10_MAX_PCT - 15))) * 40)
             + (15 if creator <= 1 else 10 if creator <= 5 else 4)
             + min(max(math.log10(max(holders, 1)) - 1.7, 0) / 2, 1) * 15   # 50 holder -> 0, 5000 -> pieno
             # Unknown lock: half, not the full 15 of a >=90% lock (v4 pools have no LP token to lock).
             + (7.5 if lp_locked is None else 15 if lp_locked >= 90 else lp_locked / 90 * 15)
             + (max(0.0, 10 - linked_pct / 2) if linked_pct is not None else max(0, 10 - 4 * insiders))
             + 5 * (tax == 0 and "tax" not in unknown))
    if unknown & {"mint", "freeze"}:
        score = min(score, 50)     # the fatal checks themselves did not run
    return _pillar("tokenomics", score, facts, flags)


async def analyze_tokenomics(chain: str, token: str, client: httpx.AsyncClient, *, pair_address: str = "",
                             exclude: set[str] | None = None, liquidity_usd: float = 0.0,
                             deep: bool = False) -> dict:
    """deep (Top 50): RugCheck's linked wallets are rebuilt and read on-chain."""
    if chain == "solana":
        report = await rugcheck_report(token, client)
        verified = None
        if deep and report and (legit.linked_share(report)[0] or 0) >= 1:
            from app.trading.onchain import linked
            try:
                verified = await linked.verify(token, report, client)
            except Exception as exc:
                logger.info("linked wallets of %s not verified: %s", token, exc)
        return judge_tokenomics_solana(report, exclude, verified)
    if chain in legit.GOPLUS_CHAIN:
        try:
            info = await legit.goplus(chain, token, client)
        except (httpx.HTTPError, ValueError):
            info = None
        if not info:
            from app.trading.onchain import research   # research builds on this module
            return judge_tokenomics_gecko(await research.gecko_info(chain, token, client))
        # What the contract holders are and when they unlock (Lorenzo, 30/09:
        # "pool e vesting devi anche trovare lo sblocco che tempi ha").
        from app.trading.onchain import unlocks
        pools = {pair_address} | {str(d.get(k) or "") for d in info.get("dex") or [] for k in ("pair", "pool_manager")}
        try:
            unl = await unlocks.annotate(chain, token, info, client, skip=pools)
        except Exception as exc:
            logger.info("unlocks of %s not read: %s", token, exc)
            unl = []
        out = judge_tokenomics_evm(info, pair_address, liquidity_usd)
        if unl:
            out.setdefault("facts", {})["unlocks"] = unl
            out.setdefault("flags", []).extend(unlocks.soon(unl))
            lp = next((u for u in unl if u["kind"] == "locker" and "LP position" in u["note"]), None)
            if lp:
                out["facts"]["lp_note"] = f"LP position held by a locker contract ({lp['note']})"
        return out
    return _pillar("tokenomics", None, {}, [], "chain not covered")


# ----------------------------------------------------------------- insieme

def overall(pillars: dict[str, dict]) -> dict:
    """{score, fatal, pending, weakest}. Un pilastro bocciato boccia tutto;
    uno in attesa lascia il progetto fuori finche' non arriva."""
    fatal = next((f"{k}: {p['fatal']}" for k, p in pillars.items() if p.get("fatal")), "")
    pending = next((f"{k}: {p['pending']}" for k, p in pillars.items() if p.get("pending")), "")
    scored = {k: p["score"] for k, p in pillars.items() if p.get("score") is not None}
    score = sum(WEIGHTS[k] * s for k, s in scored.items()) / sum(WEIGHTS[k] for k in scored) if scored else 0
    weakest = min(scored, key=scored.get) if scored else None
    return {"score": 0 if fatal else round(score, 1), "fatal": fatal, "pending": "" if fatal else pending,
            "weakest": weakest}


async def analyze(item: dict, client: httpx.AsyncClient, *, skip: set[str] = frozenset()) -> dict:
    """item: chain, token_address, pair_address, website, github, links,
    launched_at (+ bonding_curve per pump.fun). `skip`: pilastri ancora
    freschi da non rifare. Ritorna solo i pilastri rifatti, e si ferma al
    primo bocciato: le chiamate costano e il verdetto non cambierebbe."""
    out: dict[str, dict] = {}
    launched = item.get("launched_at")
    gh_links = [item.get("github") or ""] + list(item.get("links") or []) + list(item.get("websites") or [])
    if "site" not in skip:
        from app.trading.onchain import research   # research builds on this module
        out["site"], found = await research.analyze(item, client, launched)
        gh_links += found
        if out["site"]["fatal"]:
            return out
    if "github" not in skip:
        if not legit.github_targets([u for u in gh_links if u]):
            found_gh = await legit.github_find(item.get("website"), client)
            gh_links += [found_gh] if found_gh else []
        out["github"] = await analyze_github([u for u in gh_links if u], client, launched,
                                             token=item, website=item.get("website"))
        if out["github"]["fatal"]:
            return out
    if "tokenomics" not in skip:
        exclude = {x for x in (item.get("bonding_curve"), item.get("associated_bonding_curve"),
                               item.get("pair_address")) if x}
        out["tokenomics"] = await analyze_tokenomics(item["chain"], item["token_address"], client,
                                                     pair_address=item.get("pair_address") or "",
                                                     exclude=exclude,
                                                     liquidity_usd=float(item.get("liquidity_usd") or 0),
                                                     deep=bool(item.get("top")))
    return out
