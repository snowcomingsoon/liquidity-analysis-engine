"""Sectors and Today: the arenas read as a mosaic, and what changed since yesterday.

Lorenzo, 10/10, on the redesign: "opzione A, pero' dobbiamo creare anche un
mosaico per vedere le top di ogni settore in maniera intelligente", then
22/10 "applica tutto" / "SECTORS!". Direction A of the proposal
(https://claude.ai/artifact/Rr4FBJ5B9HAQxtqSBUdaAA): a Today screen with the
changes since the previous reading, and a Sectors screen with three mosaics.

- summarize(arenas): per arena the top three, its strength (how far the top
  three sit above the arena median, in spreads), the median 24h move and the
  total cap. Sectors are ordered by strength, not by how many projects they
  hold: a small sector with a clear leader beats a crowded flat one.
- record(arenas): a compact snapshot (champion and top-three average per
  sector, score of every ranked project), at most one per SNAP_GAP_S. Hourly
  for two days, then one a day for 35 days.
- today(arenas, snaps): champions changed, projects entered and dropped,
  big score moves, against the snapshot closest to a day ago.
- momentum: the top-three average now minus the one about a week ago; None
  until a snapshot at least MOMENTUM_MIN_S old exists.

Pure functions plus one JSON file on the volume; nothing here calls out.
"""
from __future__ import annotations

import json
import logging
import statistics
import time

from app.atomic_write import write_text_atomic
from app.trading.onchain import storage

logger = logging.getLogger(__name__)

TOP = 3
SNAP_GAP_S = 3600
HOURLY_KEEP_S = 2 * 86400
DAILY_KEEP_S = 35 * 86400
DAY_S = 86400
WEEK_S = 7 * 86400
MOMENTUM_MIN_S = 5 * 86400          # under five days of readings, no "week" to compare with
SPREAD_FLOOR = 5.0                  # as arenas.SPREAD_FLOOR: a point is not a spread
MOVE_MIN = 5.0                      # a score move worth a line in Today
TODAY_MAX = 40



def _file(pool: str):
    """One history per pool: the whole-row accounts rank on other rows (main._kobra_lists)."""
    return storage.data_file(f"onchain_sector_snapshots{'' if pool == 'base' else '_' + pool}.json")


def entry_id(e: dict) -> str:
    return f"{e.get('chain')}:{e.get('token_address')}"


def _score(e: dict) -> float:
    return float(e.get("score") or 0.0)


def _z(e: dict, med: float) -> float:
    z = e.get("z")
    return float(z) if z is not None else (_score(e) - med) / SPREAD_FLOOR


def _top(a: dict) -> list[dict]:
    """The arena's own top three: a copy from another narrative counts too, it
    competes there, but the leader shown first is the arena's own when tied."""
    return [e for e in a.get("entries") or []][:TOP]


def summarize(arenas: list[dict]) -> list[dict]:
    out = []
    for a in arenas:
        rows = a.get("entries") or []
        if not rows:
            continue
        med = float(a.get("median") or 0.0)
        top = _top(a)
        strength = sum(max(_z(e, med), 0.0) for e in top) / len(top)
        moves = [float(e["change_24h"]) for e in rows if e.get("change_24h") is not None and e.get("in", True)]
        out.append({
            "key": a.get("key"), "label": a.get("label"), "heat": a.get("heat") or 0,
            "size": len(rows), "median": round(med, 1),
            "strength": round(strength, 2),
            "top_avg": round(sum(_score(e) for e in top) / len(top), 1),
            "change_24h": round(statistics.median(moves), 2) if moves else None,
            "cap": round(sum(float(e.get("market_cap") or 0) for e in rows)),
            "top": top,
            "entries": rows,
        })
    out.sort(key=lambda s: (-s["strength"], -s["top_avg"]))
    return out


def snapshot(sectors: list[dict], now: float) -> dict:
    ranked: dict[str, dict] = {}
    for s in sectors:
        for e in s["entries"]:
            if not e.get("in", True):
                continue
            eid = entry_id(e)
            if eid not in ranked or _score(e) > ranked[eid]["s"]:
                ranked[eid] = {"s": round(_score(e), 1), "y": e.get("symbol") or "?", "k": s["key"]}
    return {"t": now,
            "sectors": {s["key"]: {"champ": entry_id(s["top"][0]), "sym": s["top"][0].get("symbol") or "?",
                                   "avg": s["top_avg"], "label": s["label"]} for s in sectors if s["top"]},
            "ranked": ranked}


def load(pool: str = "base") -> list[dict]:
    try:
        snaps = json.loads(_file(pool).read_text(encoding="utf-8"))
        return snaps if isinstance(snaps, list) else []
    except (OSError, ValueError):
        return []


def prune(snaps: list[dict], now: float) -> list[dict]:
    """Hourly for two days, then the first snapshot of each day."""
    keep, days = [], set()
    for s in sorted(snaps, key=lambda s: s["t"]):
        age = now - s["t"]
        if age > DAILY_KEEP_S:
            continue
        if age <= HOURLY_KEEP_S:
            keep.append(s)
            continue
        day = int(s["t"] // DAY_S)
        if day not in days:
            days.add(day)
            keep.append(s)
    return keep


def record(sectors: list[dict], now: float | None = None, snaps: list[dict] | None = None,
           persist: bool = True, pool: str = "base") -> list[dict]:
    now = time.time() if now is None else now
    snaps = load(pool) if snaps is None else snaps
    if not sectors or (snaps and now - snaps[-1]["t"] < SNAP_GAP_S):
        return snaps
    snaps = prune([*snaps, snapshot(sectors, now)], now)
    if persist:
        try:
            write_text_atomic(_file(pool), json.dumps(snaps, separators=(",", ":")))
        except OSError:
            logger.exception("sectors: snapshot not written")
    return snaps


def closest(snaps: list[dict], at: float, now: float) -> dict | None:
    """The snapshot nearest to `at` among those older than an hour; the
    oldest one if none is that old yet."""
    old = [s for s in snaps if now - s["t"] >= SNAP_GAP_S]
    if not old:
        return None
    return min(old, key=lambda s: abs(s["t"] - at))


def momentum(sectors: list[dict], snaps: list[dict], now: float) -> dict[str, float | None]:
    ref = closest(snaps, now - WEEK_S, now)
    if ref is None or now - ref["t"] < MOMENTUM_MIN_S:
        return {s["key"]: None for s in sectors}
    then = ref["sectors"]
    return {s["key"]: (round(s["top_avg"] - then[s["key"]]["avg"], 1) if s["key"] in then else None) for s in sectors}


def _gem(e: dict, s: dict) -> dict:
    return {k: e.get(k) for k in ("chain", "token_address", "symbol", "name", "image", "score",
                                   "market_cap", "liquidity_usd", "change_24h", "pair_url")} | {"sector": s["label"]}


def today(sectors: list[dict], snaps: list[dict], now: float) -> dict:
    ref = closest(snaps, now - DAY_S, now)
    if ref is None:
        return {"since": None, "items": [], "counts": {"champion": 0, "entered": 0, "dropped": 0, "moved": 0}}
    items: list[dict] = []
    now_ranked: dict[str, tuple[dict, dict]] = {}
    for s in sectors:
        for e in s["entries"]:
            if e.get("in", True):
                eid = entry_id(e)
                if eid not in now_ranked or _score(e) > _score(now_ranked[eid][0]):
                    now_ranked[eid] = (e, s)
    for s in sectors:
        was = ref["sectors"].get(s["key"])
        champ = s["top"][0]
        if was and was["champ"] != entry_id(champ):
            items.append({"kind": "champion", "gem": _gem(champ, s),
                          "text": f"{champ.get('symbol')} takes {s['label']}",
                          "detail": f"from {was['sym']} · score {round(_score(champ))}",
                          "args": {"s": champ.get("symbol"), "sector": s["label"], "was": was["sym"], "n": round(_score(champ))}})
    then = ref["ranked"]
    for eid, (e, s) in now_ranked.items():
        if eid not in then:
            items.append({"kind": "entered", "gem": _gem(e, s), "text": f"{e.get('symbol')} enters {s['label']}",
                          "detail": f"score {round(_score(e))}",
                          "args": {"s": e.get("symbol"), "sector": s["label"], "n": round(_score(e))}})
        else:
            d = _score(e) - then[eid]["s"]
            if abs(d) >= MOVE_MIN:
                items.append({"kind": "moved", "gem": _gem(e, s),
                              "text": f"{e.get('symbol')} {'gains' if d > 0 else 'loses'} {abs(round(d))} points",
                              "detail": f"{s['label']} · {round(then[eid]['s'])} → {round(_score(e))}",
                              "args": {"s": e.get("symbol"), "sector": s["label"], "d": round(d), "a": round(then[eid]["s"]), "b": round(_score(e))}})
    labels = {k: v["label"] for k, v in ref["sectors"].items()}
    for eid, was in then.items():
        if eid not in now_ranked:
            chain, _, token = eid.partition(":")
            items.append({"kind": "dropped", "gem": {"chain": chain, "token_address": token, "symbol": was["y"],
                                                     "sector": labels.get(was["k"], was["k"])},
                          "text": f"{was['y']} left the ranking",
                          "detail": f"{labels.get(was['k'], was['k'])} · was {round(was['s'])}",
                          "args": {"s": was["y"], "sector": labels.get(was["k"], was["k"]), "n": round(was["s"])}})
    order = {"champion": 0, "entered": 1, "dropped": 2, "moved": 3}
    items.sort(key=lambda i: (order[i["kind"]], -float(i["gem"].get("score") or 0)))
    counts = {k: sum(1 for i in items if i["kind"] == k) for k in order}
    return {"since": ref["t"], "items": items[:TODAY_MAX], "counts": counts}


def view(arenas: list[dict], now: float | None = None, persist: bool = True, pool: str = "base") -> dict:
    """What /api/onchain/sectors serves: sectors, momentum and Today in one read."""
    now = time.time() if now is None else now
    sectors = summarize(arenas)
    snaps = record(sectors, now, persist=persist, pool=pool)
    mom = momentum(sectors, snaps, now)
    for s in sectors:
        s["momentum"] = mom.get(s["key"])
    first = snaps[0]["t"] if snaps else None
    return {"sectors": sectors, "today": today(sectors, snaps, now),
            "readings_since": first, "momentum_ready": any(v is not None for v in mom.values())}
