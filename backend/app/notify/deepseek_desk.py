"""DeepSeek on Telegram, and the ledger of what DeepSeek does for us.

Lorenzo, 27/09: "mettiamo possibilita' di parlare con deepseek su
telegram?" and "voglio un riepilogo giornaliero di quanti token ci ha fatto
risparmiare, su telegram".

- Chat: a message to the bot (private chat, or a mention / reply / /ask in
  a group) from a known chat gets DeepSeek's answer, with the site's data
  (the system, the latest alerts, the writer's wallet and autotrader) in
  the prompt. A short memory per chat; /reset clears it. A daily token cap.
- Ledger: every DeepSeek call on the server (chat, token reviews) is
  counted per day and kind, from the API's own usage. The GitHub PR
  reviews run elsewhere; their usage rides in a hidden marker in each
  review comment and is read back from GitHub for the recap.
- Recap: once a day, in Italian: calls, tokens, what DeepSeek cost, and
  what the same tokens would have cost on Claude (an estimate at list
  prices, said as such).
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx


from app.config import settings
from app.trading.onchain.storage import data_file
from app.atomic_write import write_text_atomic

logger = logging.getLogger(__name__)

_STORE_FILE = data_file("deepseek_usage.json")
ROME = ZoneInfo("Europe/Rome")
RECAP_HOUR = 21                      # Rome time
# $ per million tokens. DeepSeek: deepseek-chat list price (cache miss).
# Claude: what these calls would have used instead (Sonnet list price).
PRICE = {"deepseek": (0.28, 0.42), "claude": (3.0, 15.0)}
CHAT_DAILY_TOKENS = 300_000
MEMORY = 10                          # messages kept per chat
KINDS = {"chat": "chat Telegram", "scanner": "scanner (giudizio token)", "research": "letture approfondite gemme",
         "review": "revisioni token", "consistency": "controllo incongruenze Top",
         "study": "studi approfonditi chiesti da Claude", "pr_review": "revisioni PR",
         "judge": "giudizi classifica", "code": "lettura codice GitHub", "narratives": "narrative",
         "meme": "giudizi meme", "retracement": "ritracciamenti", "extension": "estensioni"}

# Kinds that may use the last RESERVE of the daily cap: the Telegram chat
# and the meme alert safety vote. Everything else stops earlier.
PRIORITY_KINDS = {"chat", "meme"}
# What still reaches DeepSeek with settings.research_ai_enabled off: the
# questions people type (Lorenzo, 10/10: research "neanche deepseek").
AI_OFF_KINDS = {"chat"}
RESERVE = 0.2

_lock = threading.Lock()
# What the agent did lately, for the site's live presence (Lorenzo, 27/09:
# "deve dare l'idea di essere sempre presente [...] un agent che esamina le
# cose"). Saved with the ledger, so a restart does not empty the log.
_activity: list[dict] = []
ACTIVITY_KEEP = 1000
_state: dict = {"days": {}, "recap_sent": ""}
_memory: dict[str, list[dict]] = {}


def _load() -> None:
    try:
        raw = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(raw, dict):
        _state["days"] = raw.get("days") or {}
        _state["recap_sent"] = raw.get("recap_sent") or ""
        _state["done"] = raw.get("done") or {}
        _state["seen"] = raw.get("seen") or {}
        _state["blocked"] = raw.get("blocked") or {}
        _activity[:] = [a for a in raw.get("activity") or [] if isinstance(a, dict)][-ACTIVITY_KEEP:]


def _save() -> None:
    try:
        write_text_atomic(_STORE_FILE, json.dumps({**_state, "activity": _activity}, separators=(",", ":")), encoding="utf-8")
    except OSError:
        pass


def reset_for_tests() -> None:
    global _reserved
    _reserved = 0.0
    _state.update(days={}, recap_sent="", done={}, seen={}, blocked={})
    _memory.clear()
    _activity.clear()


def note(kind: str, text: str, now: float | None = None,
         steps: list[str] | None = None, outcome: str = "", tally: bool = True, **extra) -> None:
    """One line of what the agent is doing, for /api/agent. `tally=False`:
    a detail of work already counted (a finding of a check)."""
    now = now or time.time()
    entry = {"t": now, "kind": kind, "text": text[:140], **extra}
    # What the agent did today, by kind: every job, not only the LLM calls
    # (a backtest or a GitHub study costs no tokens but is real work).
    done = _state.setdefault("done", {})
    day = done.setdefault(day_of(now), {})
    if tally:
        day[kind] = day.get(kind, 0) + 1
    for old in sorted(done)[:-3]:
        done.pop(old, None)
    # Distinct tokens per kind: a project studied 30 times is one project.
    if extra.get("token"):
        seen = _state.setdefault("seen", {})
        keys = seen.setdefault(day_of(now), {}).setdefault(kind, [])
        key = f"{extra.get('chain') or ''}:{extra['token']}"
        if key not in keys:
            keys.append(key)
        for old in sorted(seen)[:-1]:
            seen.pop(old, None)
    if steps:
        entry["steps"] = [str(s)[:200] for s in steps][:8]
    if outcome:
        entry["outcome"] = str(outcome)[:200]
    _activity.append(entry)
    del _activity[:-ACTIVITY_KEEP]
    _save()


def log(limit: int = 100, before: float | None = None) -> list[dict]:
    """Newest first, entries older than `before` when given."""
    items = [a for a in _activity if before is None or a.get("t", 0) < before]
    return list(reversed(items[-limit:]))


def activity(now: float | None = None) -> dict:
    now = now or time.time()
    today = _state["days"].get(day_of(now)) or {}
    try:
        from app.trading.onchain import priority
        prio = priority.backtests_first()
    except Exception:
        prio = None
    return {"items": list(reversed(_activity[-30:])),
            "done": dict((_state.get("done") or {}).get(day_of(now)) or {}),
            "working": bool(_activity) and now - _activity[-1]["t"] < 180,
            "today": {k: v.get("calls", 0) for k, v in today.items()},
            "spent_usd": round(spent_usd_today(now), 4),
            "cap_usd": float(settings.deepseek_daily_usd or 0),
            "tokens": sum(int(v.get("in", 0)) + int(v.get("out", 0)) for v in today.values()),
            "distinct": {k: len(v) for k, v in ((_state.get("seen") or {}).get(day_of(now)) or {}).items()},
            "active": _free_ai_on(),
            "priority": prio}


def _free_ai_on() -> bool:
    from app import free_ai
    return free_ai.available()


def day_of(ts: float) -> str:
    return datetime.fromtimestamp(ts, ROME).strftime("%Y-%m-%d")


def record(kind: str, tokens_in: int, tokens_out: int, now: float | None = None) -> None:
    now = now or time.time()
    with _lock:
        day = _state["days"].setdefault(day_of(now), {})
        k = day.setdefault(kind, {"calls": 0, "in": 0, "out": 0})
        k["calls"] += 1
        k["in"] += int(tokens_in or 0)
        k["out"] += int(tokens_out or 0)
        cutoff = day_of(now - 60 * 86400)
        _state["days"] = {d: v for d, v in _state["days"].items() if d >= cutoff}
        _save()


def spent_today(kind: str, now: float | None = None) -> int:
    k = (_state["days"].get(day_of(now or time.time())) or {}).get(kind) or {}
    return int(k.get("in", 0)) + int(k.get("out", 0))


def cost(provider: str, tokens_in: int, tokens_out: int) -> float:
    p_in, p_out = PRICE[provider]
    return (tokens_in * p_in + tokens_out * p_out) / 1e6


class BudgetExceeded(RuntimeError):
    """The daily DeepSeek cap is spent: the call was not sent."""


_reserved = 0.0   # $ of calls in flight, so parallel calls cannot overshoot


def spent_usd_today(now: float | None = None) -> float:
    rows = _state["days"].get(day_of(now or time.time())) or {}
    return sum(cost("deepseek", int(v.get("in", 0)), int(v.get("out", 0))) for v in rows.values())


def _reserve(kind: str, messages: list[dict], max_tokens: int, now: float | None = None) -> float:
    """Book the worst case of one call against the daily cap, or refuse it."""
    global _reserved
    cap = float(settings.deepseek_daily_usd or 0)
    tokens_in = len(json.dumps(messages, ensure_ascii=False)) // 3
    need = cost("deepseek", tokens_in, max_tokens)
    if cap <= 0:
        return 0.0
    limit = cap if kind in PRIORITY_KINDS else cap * (1 - RESERVE)
    with _lock:
        if spent_usd_today(now) + _reserved + need > limit:
            blocked = _state.setdefault("blocked", {})
            day = blocked.setdefault(day_of(now or time.time()), {})
            day[kind] = day.get(kind, 0) + 1
            for old in sorted(blocked)[:-3]:
                blocked.pop(old, None)
            _save()
            raise BudgetExceeded(f"DeepSeek daily cap ${cap:.2f} reached ({kind})")
        _reserved += need
    return need


def _release(need: float) -> None:
    global _reserved
    with _lock:
        _reserved = max(0.0, _reserved - need)


# ------------------------------------------------------------------ DeepSeek

async def _post(body: dict, *, kind: str, purpose: str | None, subject: str | None, http=None) -> dict:
    """One call to the chat API: counted in the ledger and in the call
    journal (deepseek_calls, issue #358 I00), failures included."""
    from app.notify import deepseek_calls
    # DeepSeek is gone (Lorenzo, 20/10: "considera DeepSeek ad oggi come se
    # non esistesse"): every call, the chat included, goes to the free AI
    # (free_ai.py: Groq, then Gemini), at no cost and off the ledger.
    from app import free_ai
    if not free_ai.available():
        raise BudgetExceeded(f"no free AI key set for {kind} (Diagnostics)")
    t0 = time.monotonic()
    try:
        data = await free_ai.post(body, kind=kind, http=http)
    except free_ai.Unavailable as exc:
        deepseek_calls.log(kind=kind, purpose=purpose, subject=subject, body=body, content=None, usage=None,
                           ms=(time.monotonic() - t0) * 1000, error=f"free AI: {exc}")
        raise BudgetExceeded(f"free AI: {exc}") from exc
    logger.info("free ai: %s answered %s", f"{data['provider']}/{data['model']}", kind)
    deepseek_calls.log(kind=kind, purpose=purpose, subject=subject, body=body, content=free_ai.content(data),
                       usage=data.get("usage"),
                       ms=(time.monotonic() - t0) * 1000)
    return data


async def ask_message(messages: list[dict], *, kind: str, max_tokens: int = 1200, tools: list[dict] | None = None,
                      http=None, purpose: str | None = None, subject: str | None = None) -> dict:
    """One call, returning DeepSeek's whole message (content and tool_calls)."""
    body = {"model": settings.deepseek_model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.4}
    if tools:
        body["tools"] = tools
    data = await _post(body, kind=kind, purpose=purpose, subject=subject, http=http)
    return ((data.get("choices") or [{}])[0].get("message") or {})


async def ask(messages: list[dict], *, kind: str, max_tokens: int = 1200, http=None, json_mode: bool = False,
              purpose: str | None = None, subject: str | None = None) -> str:
    """One DeepSeek chat call, counted in the ledger under `kind` and in the
    call journal under `purpose`/`subject`. Keep the system message
    identical between calls: DeepSeek caches a repeated prefix and bills it
    at a tenth."""
    body = {"model": settings.deepseek_model, "messages": messages, "max_tokens": max_tokens,
            "temperature": 0 if json_mode else 0.4}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = await _post(body, kind=kind, purpose=purpose, subject=subject, http=http)
    return (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


CHAT_SYSTEM = (
    "Sei l'assistente di Liquidity Engine (liquidityengine.app), un sito che segnala meme coin e gemme "
    "on-chain (Solana, Robinhood Chain, BSC, Base, Ethereum) e le segue con un sistema trend-following "
    "(ingresso e uscita automatici, finestra 48h). Rispondi in italiano, breve e concreto, come in chat. "
    "Usa i dati del sito qui sotto quando servono e non inventare numeri che non ci sono: se un dato manca, "
    "dillo. Non promettere guadagni: sono mercati molto rischiosi. Non chiedere mai chiavi private o seed. "
    "Hai strumenti per leggere tutto il database del sito (progetti, classifica gemme, alert, sistema, scartati, "
    "memoria dei rug, strategie sniper, backtest gemme, laboratorio, review giornaliere, scanner, diario dell'agente, "
    "dettagli di un token): usali invece di tirare a indovinare. Se ti chiedono di segnalare un problema, o vedi dati "
    "incoerenti, usa segnala_bug: la segnalazione va sulla bacheca e Claude la verifica e la risolve.")


def wants_answer(message: dict, bot_username: str) -> str | None:
    """The text to answer, or None. Private chat: every text. Group: only
    /ask, a mention of the bot, or a reply to it."""
    text = (message.get("text") or "").strip()
    if not text:
        return None
    chat = message.get("chat") or {}
    if chat.get("type") == "private":
        return re.sub(r"^/ask(@\w+)?\s*", "", text) or None
    mention = f"@{bot_username}".lower() if bot_username else None
    reply_to_bot = ((message.get("reply_to_message") or {}).get("from") or {}).get("username", "").lower() == (bot_username or "").lower()
    if re.match(r"^/ask(@\w+)?\b", text):
        return re.sub(r"^/ask(@\w+)?\s*", "", text) or None
    if mention and mention in text.lower():
        return re.sub(re.escape(f"@{bot_username}"), "", text, flags=re.I).strip() or None
    if reply_to_bot and bot_username:
        return text
    return None


TOOL_ROUNDS = 5

# Standing instructions Lorenzo gives on Telegram (29/09: "voglio poterlo
# auto istruire"). Only the owner's chats (telegram_chat_ids) can add or
# remove them; every chat's answers follow them. They steer answers, never
# grant anything: no keys, no money moves, no rule changes on the server.
_INSTR_FILE = data_file("deepseek_instructions.json")
MAX_INSTRUCTIONS = 30
INSTRUCTION_CHARS = 400
_instructions: list[dict] = []


def _load_instructions() -> None:
    try:
        raw = json.loads(_INSTR_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(raw, list):
        _instructions[:] = [i for i in raw if isinstance(i, dict) and i.get("text")][:MAX_INSTRUCTIONS]


def _save_instructions() -> None:
    try:
        tmp = _INSTR_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_instructions, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_INSTR_FILE)
    except OSError:
        logger.exception("deepseek: istruzioni non salvate")


def instructions() -> list[dict]:
    return [{"n": i + 1, "text": x["text"], "at": x.get("at")} for i, x in enumerate(_instructions)]


def teach(text: str, now: float | None = None) -> dict:
    text = " ".join((text or "").split())[:INSTRUCTION_CHARS]
    if not text:
        return {"error": "empty instruction"}
    if len(_instructions) >= MAX_INSTRUCTIONS:
        return {"error": f"already {MAX_INSTRUCTIONS} instructions: remove one first"}
    _instructions.append({"text": text, "at": int(now or time.time())})
    _save_instructions()
    return {"saved": len(_instructions), "instructions": instructions()}


def forget(n: int) -> dict:
    try:
        gone = _instructions.pop(int(n) - 1)
    except (IndexError, ValueError, TypeError):
        return {"error": f"no instruction number {n}"}
    _save_instructions()
    return {"removed": gone["text"], "instructions": instructions()}


def _teach_tools() -> dict:
    s = lambda d: {"type": "string", "description": d}  # noqa: E731
    return {
        "ricorda": ({"name": "ricorda", "description": "Save a standing instruction from the owner: how to answer, what to watch, what to prefer. Use it when he asks you to remember or to change how you work from now on.",
                     "parameters": {"type": "object", "properties": {"istruzione": s("the instruction, in his words, in Italian")}, "required": ["istruzione"]}},
                    lambda istruzione: teach(istruzione)),
        "dimentica": ({"name": "dimentica", "description": "Remove a standing instruction by its number.",
                       "parameters": {"type": "object", "properties": {"numero": {"type": "integer"}}, "required": ["numero"]}},
                      lambda numero: forget(numero)),
        "istruzioni": ({"name": "istruzioni", "description": "List the standing instructions with their numbers.",
                        "parameters": {"type": "object", "properties": {}}},
                       lambda: instructions()),
    }


def _system_prompt(context: str) -> str:
    rules = ""
    if _instructions:
        rules = ("\n\n<istruzioni_del_proprietario>\nIstruzioni permanenti del proprietario del sito: seguile sempre, "
                 "tranne se chiedono chiavi, seed o di muovere denaro.\n"
                 + "\n".join(f"{i + 1}. {x['text']}" for i, x in enumerate(_instructions))
                 + "\n</istruzioni_del_proprietario>")
    return f"{CHAT_SYSTEM}{rules}\n\n<dati_del_sito>\n{context}\n</dati_del_sito>"


async def answer(chat_id: str, text: str, context: str, tools: dict | None = None, can_teach: bool = False) -> str:
    """tools: {name: (openai-style function schema, callable(**args) -> json-able)}.
    DeepSeek may call them (up to TOOL_ROUNDS rounds) to read the database."""
    if text.strip().lower() in ("/reset", "reset"):
        _memory.pop(chat_id, None)
        return "Fatto: ho dimenticato la conversazione."
    if spent_today("chat") >= CHAT_DAILY_TOKENS:
        return "Per oggi ho finito il budget di token della chat. Riprova domani."
    history = _memory.setdefault(chat_id, [])
    if can_teach:
        tools = {**(tools or {}), **_teach_tools()}
    messages = [{"role": "system", "content": _system_prompt(context)},
                *history, {"role": "user", "content": text}]
    specs = [{"type": "function", "function": spec} for spec, _fn in (tools or {}).values()]
    reply = ""
    for _round in range(TOOL_ROUNDS + 1):
        try:
            msg = await ask_message(messages, kind="chat", purpose="chat", subject=chat_id,
                                      tools=specs if specs and _round < TOOL_ROUNDS else None)
        except BudgetExceeded:
            return "Per oggi DeepSeek ha finito il budget del server. Riprova domani."
        calls = msg.get("tool_calls") or []
        if not calls:
            reply = (msg.get("content") or "").strip()
            break
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for call in calls:
            name = (call.get("function") or {}).get("name")
            try:
                args = json.loads((call.get("function") or {}).get("arguments") or "{}")
                result = tools[name][1](**args)
            except Exception as exc:
                result = {"error": f"{type(exc).__name__}: {exc}"[:200]}
            messages.append({"role": "tool", "tool_call_id": call.get("id"),
                             "content": json.dumps(result, default=str)[:6000]})
    reply = reply or "Non ho una risposta."
    history += [{"role": "user", "content": text}, {"role": "assistant", "content": reply}]
    del history[:-MEMORY]
    return reply


# ------------------------------------------------------------------ recap

MARK_RE = re.compile(r"<!-- deepseek-usage (\{.*?\}) -->")


async def pr_review_usage(since: float, until: float, http=None) -> dict:
    """The PR reviews' usage, from the markers in their GitHub comments."""
    repo = settings.github_repo
    out = {"calls": 0, "in": 0, "out": 0}
    if not settings.github_api_token:
        return out
    iso = datetime.fromtimestamp(since, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {"Authorization": f"Bearer {settings.github_api_token}", "Accept": "application/vnd.github+json"}
    own = http is None
    http = http or httpx.AsyncClient(timeout=20.0)
    try:
        r = await http.get(f"https://api.github.com/repos/{repo}/issues/comments",
                           params={"since": iso, "per_page": 100}, headers=headers)
        rows = r.json() if r.status_code == 200 else []
    except httpx.HTTPError:
        rows = []
    finally:
        if own:
            await http.aclose()
    for c in rows if isinstance(rows, list) else []:
        for m in MARK_RE.finditer(c.get("body") or ""):
            try:
                u = json.loads(m[1])
                at = float(u.get("at") or 0)
            except (ValueError, TypeError):
                continue
            if since <= at < until:
                out["calls"] += 1
                out["in"] += int(u.get("in", 0))
                out["out"] += int(u.get("out", 0))
    return out


def _n(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def recap_text(day: str, rows: dict) -> str:
    """rows: {kind: {calls, in, out}}. Italian, for Lorenzo."""
    lines = [f"🤖 <b>DeepSeek — {datetime.strptime(day, '%Y-%m-%d').strftime('%d/%m')}</b>"]
    tot_in = tot_out = calls = 0
    # Every kind recorded, not only the labelled ones: an unlabelled kind
    # still costs tokens and must be in the total.
    kinds = list(KINDS) + sorted(k for k in rows if k not in KINDS)
    for kind in kinds:
        label = KINDS.get(kind, kind)
        k = rows.get(kind) or {}
        if not k.get("calls"):
            continue
        calls += k["calls"]
        tot_in += k["in"]
        tot_out += k["out"]
        lines.append(f"• {label}: {k['calls']} richieste, {_n(k['in'] + k['out'])} token")
    if not calls:
        return "\n".join(lines + ["Oggi nessun lavoro per DeepSeek."])
    ds, cl = cost("deepseek", tot_in, tot_out), cost("claude", tot_in, tot_out)
    lines += ["",
              f"Token lavorati da DeepSeek: <b>{_n(tot_in + tot_out)}</b> ({_n(tot_in)} letti, {_n(tot_out)} scritti)",
              f"Costo DeepSeek: <b>${ds:.3f}</b> · con Claude sarebbero stati ~${cl:.2f}",
              f"Risparmio stimato: <b>${cl - ds:.2f}</b> (prezzi di listino)"]
    blocked = (_state.get("blocked") or {}).get(day) or {}
    if blocked:
        lines.append(f"Fermate dal tetto di ${float(settings.deepseek_daily_usd or 0):.2f}: "
                     + ", ".join(f"{KINDS.get(k, k)} {n}" for k, n in sorted(blocked.items())))
    return "\n".join(lines)


def recap_due(now: float) -> str | None:
    """The day to recap (yesterday or today at RECAP_HOUR), if not sent yet."""
    local = datetime.fromtimestamp(now, ROME)
    if local.hour < RECAP_HOUR:
        return None
    day = local.strftime("%Y-%m-%d")
    return None if _state["recap_sent"] == day else day


def mark_sent(day: str) -> None:
    _state["recap_sent"] = day
    _save()


def day_bounds(day: str) -> tuple[float, float]:
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=ROME)
    return start.timestamp(), (start + timedelta(days=1)).timestamp()


_load()


_load_instructions()
