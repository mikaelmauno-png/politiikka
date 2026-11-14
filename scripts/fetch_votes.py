"""Plenary roll-call votes of the current parliamentary term from the Eduskunta open data API.

Uses the API's primary-key "batch" endpoint (fast, ordered) instead of filtered queries
(slow). Incremental: data/cache/votes_state.json remembers where the previous run stopped.

data/cache/votes.jsonl, one vote per line:
  {"id","t" (start time),"title","item","doc","res":[jaa,ei,tyhja,poissa],
   "g": {group: "J1504 E1306 P..."}}      J=jaa, E=ei, T=tyhjä, P=poissa
data/cache/mps.json: {henkilonumero: "Etunimi Sukunimi"}
"""
import json
import os
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from common import CACHE, get_json, read_json, write_json

API = "https://avoindata.eduskunta.fi/api/v1/tables/"
TERM_START = "2023-04-12"     # first sitting of the 2023 parliament
FIRST_VOTE_SCAN = 48000       # AanestysId comfortably before the term start
VOTES = f"{CACHE}/votes.jsonl"
MPS = f"{CACHE}/mps.json"
STATE = f"{CACHE}/votes_state.json"
CODES = {"jaa": "J", "ei": "E", "tyhjää": "T", "tyhjia": "T", "tyhjiä": "T", "poissa": "P"}
WORKERS = 6


def s(v):
    return (v or "").strip()


def batch(table, pk, start):
    q = urllib.parse.urlencode({"pkName": pk, "pkStartValue": start, "perPage": 100})
    d = get_json(f"{API}{table}/batch?{q}")
    return [dict(zip(d["columnNames"], r)) for r in d["rowData"]], d["hasMore"]


def scan(table, pk, lo, hi=None):
    """All rows with lo < pk (<= hi), in order. The API's pkStartValue is inclusive."""
    out, cur = [], lo + 1
    while True:
        rows, more = batch(table, pk, cur)
        if not rows:
            return out
        for r in rows:
            if hi is not None and int(r[pk]) > hi:
                return out
            out.append(r)
        cur = int(rows[-1][pk]) + 1
        if not more:
            return out


def filtered(table, column, value):
    q = urllib.parse.urlencode({"columnName": column, "columnValue": value, "perPage": 100})
    d = get_json(f"{API}{table}/rows?{q}")
    return [dict(zip(d["columnNames"], r)) for r in d["rowData"]]


def vote_meta(start):
    meta, max_id = {}, start
    for r in scan("SaliDBAanestys", "AanestysId", start):
        max_id = max(max_id, int(r["AanestysId"]))
        t = s(r["AanestysAlkuaika"])
        if s(r["KieliId"]) != "1" or s(r["AanestysMitatoity"]) != "0" or t < TERM_START:
            continue
        meta[int(r["AanestysId"])] = {
            "id": int(r["AanestysId"]), "t": t[:16],
            "title": s(r["AanestysOtsikko"]), "item": s(r["KohtaOtsikko"]),
            "doc": s(r["AanestysValtiopaivaasia"]),
            "res": [int(s(r[k]) or 0) for k in ("AanestysTulosJaa", "AanestysTulosEi",
                                                "AanestysTulosTyhjia", "AanestysTulosPoissa")],
        }
    return meta, max_id


def mp_rows(start, upper_hint):
    """Scan SaliDBAanestysEdustaja from `start`, in parallel chunks up to `upper_hint`, then onward."""
    span = max(0, upper_hint - start)
    if span < 50_000:
        return scan("SaliDBAanestysEdustaja", "EdustajaId", start)
    step = span // WORKERS + 1
    bounds = [(start + i * step, start + (i + 1) * step) for i in range(WORKERS)]
    bounds[-1] = (bounds[-1][0], None)  # last chunk runs to the end
    with ThreadPoolExecutor(WORKERS) as ex:
        parts = ex.map(lambda b: scan("SaliDBAanestysEdustaja", "EdustajaId", b[0], b[1]), bounds)
        return [r for part in parts for r in part]


def main():
    have = set()
    if os.path.exists(VOTES):
        with open(VOTES, encoding="utf-8") as f:
            have = {json.loads(l)["id"] for l in f if l.strip()}
    state = read_json(STATE, {})
    meta, max_aid = vote_meta(state.get("aanestysStart", FIRST_VOTE_SCAN))
    meta = {k: v for k, v in meta.items() if k not in have}
    print(f"votes cached {len(have)}, new metadata {len(meta)}", flush=True)
    if not meta:
        return

    ids = sorted(meta)
    e_start = state.get("edustajaStart")
    if e_start is None:  # first run: locate the first MP row of the term
        first = filtered("SaliDBAanestysEdustaja", "AanestysId", ids[0])
        e_start = min(int(r["EdustajaId"]) for r in first) - 1
    last = filtered("SaliDBAanestysEdustaja", "AanestysId", ids[-1])
    upper = max((int(r["EdustajaId"]) for r in last), default=e_start)

    rows = mp_rows(e_start, upper)
    print(f"MP rows scanned {len(rows)}", flush=True)
    by_vote = defaultdict(list)
    max_eid = e_start
    for r in rows:
        max_eid = max(max_eid, int(r["EdustajaId"]))
        aid = int(r["AanestysId"])
        if aid in meta:
            by_vote[aid].append(r)

    mps = read_json(MPS, {})
    done, incomplete = [], []
    for aid in ids:
        v, rs = meta[aid], by_vote.get(aid, [])
        if len(rs) < sum(v["res"]) or not rs:
            incomplete.append(aid)
            continue
        groups = defaultdict(list)
        for r in rs:
            code = CODES.get(s(r["EdustajaAanestys"]).lower())
            if not code:
                continue
            hn = s(r["EdustajaHenkiloNumero"])
            groups[s(r["EdustajaRyhmaLyhenne"]).lower()].append(code + hn)
            mps[hn] = f"{s(r['EdustajaEtunimi'])} {s(r['EdustajaSukunimi'])}"
        v["g"] = {g: " ".join(x) for g, x in sorted(groups.items())}
        done.append(v)

    with open(VOTES, "a", encoding="utf-8") as f:
        for v in done:
            f.write(json.dumps(v, ensure_ascii=False, separators=(",", ":")) + "\n")
    write_json(MPS, dict(sorted(mps.items(), key=lambda kv: int(kv[0]))), compact=False)

    # Next run: resume before the earliest incomplete vote, otherwise after what we saw.
    if incomplete:
        partial = [int(r["EdustajaId"]) for a in incomplete for r in by_vote.get(a, [])]
        state = {"aanestysStart": min(incomplete) - 1,
                 "edustajaStart": (min(partial) - 1) if partial else max_eid}
    else:
        state = {"aanestysStart": max_aid, "edustajaStart": max_eid}
    write_json(STATE, state, compact=False)
    print(f"appended {len(done)} votes, incomplete {len(incomplete)}, state {state}")


if __name__ == "__main__":
    main()
