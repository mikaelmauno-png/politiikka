"""Derive everything the page shows from the cached raw data -> data/site.json."""
import datetime
import json
import math
import os
from collections import defaultdict
from zoneinfo import ZoneInfo

from common import CACHE, DATA, GOVERNMENT, PARTIES, read_json, write_json

OPPOSITION = [p for p in PARTIES if p not in GOVERNMENT]
GROUP2PARTY = {"kok": "KOK", "ps": "PS", "sd": "SDP", "kesk": "KESK", "vas": "VAS",
               "vihr": "VIHR", "r": "RKP", "kd": "KD", "liik": "LIIK"}

# Governments since 1983 (main parties; mid-term exits noted in "note").
GOVERNMENTS = [
    {"name": "Sorsa IV", "start": "1983-05", "end": "1987-04", "parties": ["SDP", "KESK", "RKP"], "note": "myös SMP"},
    {"name": "Holkeri", "start": "1987-04", "end": "1991-04", "parties": ["KOK", "SDP", "RKP"], "note": "SMP 1990 asti"},
    {"name": "Aho", "start": "1991-04", "end": "1995-04", "parties": ["KESK", "KOK", "RKP", "KD"], "note": "SKL 1994 asti"},
    {"name": "Lipponen I", "start": "1995-04", "end": "1999-04", "parties": ["SDP", "KOK", "VAS", "VIHR", "RKP"]},
    {"name": "Lipponen II", "start": "1999-04", "end": "2003-04", "parties": ["SDP", "KOK", "VAS", "VIHR", "RKP"], "note": "VIHR 2002 asti"},
    {"name": "Jäätteenmäki / Vanhanen I", "start": "2003-04", "end": "2007-04", "parties": ["KESK", "SDP", "RKP"]},
    {"name": "Vanhanen II / Kiviniemi", "start": "2007-04", "end": "2011-06", "parties": ["KESK", "KOK", "VIHR", "RKP"]},
    {"name": "Katainen / Stubb", "start": "2011-06", "end": "2015-05", "parties": ["KOK", "SDP", "VAS", "VIHR", "RKP", "KD"], "note": "VAS ja VIHR 2014 asti"},
    {"name": "Sipilä", "start": "2015-05", "end": "2019-06", "parties": ["KESK", "PS", "KOK"], "note": "PS:n tilalle Sininen tulevaisuus 2017"},
    {"name": "Rinne / Marin", "start": "2019-06", "end": "2023-06", "parties": ["SDP", "KESK", "VIHR", "VAS", "RKP"]},
    {"name": "Orpo", "start": "2023-06", "end": None, "parties": ["KOK", "PS", "RKP", "KD"]},
]


def month_add(ym, n):
    y, m = int(ym[:4]), int(ym[5:7]) - 1 + n
    return f"{y + m // 12:04d}-{m % 12 + 1:02d}"


def months_between(a, b):
    out = [a]
    while out[-1] < b:
        out.append(month_add(out[-1], 1))
    return out


def ml(ym):
    return f"{int(ym[5:7])}/{ym[:4]}"


def phase(level, change):
    if level >= 0:
        return "nousu" if change >= 0 else "hidastuminen"
    return "elpyminen" if change >= 0 else "lasku"


def r1(x, d=1):
    return None if x is None else round(x, d)


# ---------------------------------------------------------------- polls
def build_polls(raw, today):
    polls, e = raw["polls"], raw["election2023"]
    base = {p: e[p] for p in PARTIES}
    base["HALLITUS"] = sum(e[p] for p in GOVERNMENT)
    base["OPPOSITIO"] = sum(e[p] for p in OPPOSITION)
    series_keys = PARTIES + ["HALLITUS", "OPPOSITIO"]

    months = months_between("2023-04", today.strftime("%Y-%m"))
    monthly, last = {}, None
    for m in months:
        latest_by_firm = {}
        for p in sorted(polls, key=lambda p: p["date"]):
            if p["date"][:7] == m:
                latest_by_firm[p["firm"]] = p
        if latest_by_firm:
            vals = {k: sum(p[k] for p in latest_by_firm.values()) / len(latest_by_firm) for k in PARTIES}
            vals["HALLITUS"] = sum(vals[k] for k in GOVERNMENT)
            vals["OPPOSITIO"] = sum(vals[k] for k in OPPOSITION)
            last = vals
        monthly[m] = last
    months = [m for m in months if monthly[m]]

    def smooth(i, k):
        win = [monthly[months[j]][k] for j in range(max(0, i - 2), i + 1)]
        return sum(win) / len(win)

    series = {k: [] for k in series_keys}
    for i, m in enumerate(months):
        for k in series_keys:
            s = smooth(i, k)
            prev = smooth(i - 3, k) if i >= 3 else None
            level = s - base[k]
            change = s - prev if prev is not None else 0.0
            series[k].append({"m": m, "raw": r1(monthly[m][k], 2), "avg": r1(s, 2),
                              "level": r1(level, 2), "change": r1(change, 2),
                              "phase": phase(level, change)})
    # Latest snapshot: latest poll per firm in the last 45 days
    cutoff = (today - datetime.timedelta(days=45)).isoformat()
    recent = {}
    for p in sorted(polls, key=lambda p: p["date"]):
        if p["date"] >= cutoff:
            recent[p["firm"]] = p
    if not recent:
        recent = {polls[0]["firm"]: polls[0]}
    latest = {k: sum(p[k] for p in recent.values()) / len(recent) for k in PARTIES}
    return {"months": months, "series": series, "election2023": base,
            "latest": {k: r1(v, 2) for k, v in latest.items()},
            "latestPolls": [{"firm": f, "date": p["date"]} for f, p in recent.items()],
            "polls": polls, "source": raw["source"]}


# ---------------------------------------------------------------- seat projection
def dhondt(votes, seats):
    alloc = {p: 0 for p in votes}
    for _ in range(seats):
        best = max(votes, key=lambda p: votes[p] / (alloc[p] + 1))
        alloc[best] += 1
    return alloc


def build_seats(elections, latest):
    nat = elections["national"]["2023"]
    swing = {p: latest[p] / nat[p] for p in PARTIES if nat.get(p)}
    total = {p: 0 for p in PARTIES}
    total["Muut"] = 0
    districts = []
    for vp, d in sorted(elections["districts"].items()):
        if vp == "VP05":  # Åland elects one MP from its own lists
            total["Muut"] += d["seats"]
            districts.append({"vp": vp, "name": d["name"], "seats": {"Muut": d["seats"]}})
            continue
        votes = {p: d["votes"].get(p, 0) * swing[p] for p in PARTIES if d["votes"].get(p)}
        alloc = dhondt(votes, d["seats"])
        for p, s in alloc.items():
            total[p] += s
        districts.append({"vp": vp, "name": d["name"], "seats": {p: s for p, s in alloc.items() if s}})
    gov = sum(total[p] for p in GOVERNMENT)
    return {"total": total, "government": gov, "districts": districts,
            "seats2023": {"KOK": 48, "PS": 46, "SDP": 43, "KESK": 23, "VIHR": 13, "VAS": 11,
                          "RKP": 9, "KD": 5, "LIIK": 1, "Muut": 1}}


# ---------------------------------------------------------------- parliament votes
def load_votes():
    votes = []
    path = f"{CACHE}/votes.jsonl"
    if not os.path.exists(path):
        return votes
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            v = json.loads(line)
            ballots, seen = [], set()  # (henkilonumero, party, code)
            for g, s in v["g"].items():
                party = GROUP2PARTY.get(g, g.upper())
                for tok in s.split():
                    if tok[1:] not in seen:
                        seen.add(tok[1:])
                        ballots.append((tok[1:], party, tok[0]))
            v["ballots"] = ballots
            votes.append(v)
    votes.sort(key=lambda v: (v["t"], v["id"]))
    return votes


def line_of(counts):
    j, e = counts.get("J", 0), counts.get("E", 0)
    if j > e:
        return "J"
    if e > j:
        return "E"
    return None


def build_parliament(votes, mps):
    party_month = defaultdict(lambda: defaultdict(lambda: {"present": 0, "all": 0, "coh": 0.0, "n": 0}))
    month_stats = defaultdict(lambda: {"votes": 0, "defeats": 0, "close": 0, "rebel": 0})
    agree = defaultdict(lambda: [0, 0])
    agree12 = defaultdict(lambda: [0, 0])
    mp = defaultdict(lambda: {"votes": 0, "present": 0, "rebel": 0, "party": None})
    defeats, rebels_list = [], []
    last_month = votes[-1]["t"][:7] if votes else None
    cutoff12 = month_add(last_month, -11) if last_month else None

    for v in votes:
        m = v["t"][:7]
        counts = defaultdict(lambda: defaultdict(int))
        for hn, party, code in v["ballots"]:
            counts[party][code] += 1
        lines = {p: line_of(c) for p, c in counts.items()}
        jaa, ei = v["res"][0], v["res"][1]
        result = "J" if jaa > ei else "E"
        gov_counts = defaultdict(int)
        for p in GOVERNMENT:
            for code, n in counts.get(p, {}).items():
                gov_counts[code] += n
        gov_line = line_of(gov_counts)
        contested = jaa + ei > 0 and min(jaa, ei) / (jaa + ei) >= 0.10
        ms = month_stats[m]
        ms["votes"] += 1
        if abs(jaa - ei) <= 10:
            ms["close"] += 1
        if gov_line and gov_line != result:
            ms["defeats"] += 1
            defeats.append({"t": v["t"], "title": v["title"], "item": v["item"], "doc": v["doc"],
                            "res": v["res"]})
        for p, c in counts.items():
            if p not in PARTIES:
                continue
            present = c.get("J", 0) + c.get("E", 0) + c.get("T", 0)
            pm = party_month[p][m]
            pm["present"] += present
            pm["all"] += present + c.get("P", 0)
            if present and contested:
                mx = max(c.get("J", 0), c.get("E", 0), c.get("T", 0))
                pm["coh"] += (mx - 0.5 * (present - mx)) / present  # Hix agreement index
                pm["n"] += 1
        ps = [p for p in PARTIES if lines.get(p)]
        for i, a in enumerate(ps):
            for b in ps[i + 1:]:
                same = lines[a] == lines[b]
                agree[(a, b)][0] += same
                agree[(a, b)][1] += 1
                if m >= cutoff12:
                    agree12[(a, b)][0] += same
                    agree12[(a, b)][1] += 1
        for hn, party, code in v["ballots"]:
            r = mp[hn]
            r["votes"] += 1
            r["party"] = party
            if code != "P":
                r["present"] += 1
            if code in "JE" and lines.get(party) and code != lines[party]:
                r["rebel"] += 1
                ms["rebel"] += 1

    months = sorted(month_stats)
    party_series = {}
    for p in PARTIES:
        party_series[p] = [{"m": m,
                            "attendance": r1(100 * party_month[p][m]["present"] / party_month[p][m]["all"], 1)
                            if party_month[p][m]["all"] else None,
                            "cohesion": r1(100 * party_month[p][m]["coh"] / party_month[p][m]["n"], 1)
                            if party_month[p][m]["n"] else None}
                           for m in months]

    def matrix(src):
        out = {}
        for (a, b), (s, n) in src.items():
            if n:
                out[f"{a}-{b}"] = out[f"{b}-{a}"] = r1(100 * s / n, 1)
        return out

    mp_rows = []
    for hn, r in mp.items():
        if r["votes"] < 50:
            continue
        mp_rows.append({"hn": hn, "name": mps.get(hn, hn), "party": r["party"], "votes": r["votes"],
                        "attendance": r1(100 * r["present"] / r["votes"], 1),
                        "rebel": r["rebel"], "rebelPct": r1(100 * r["rebel"] / max(1, r["present"]), 2)})
    mp_rows.sort(key=lambda r: (-r["rebel"], r["name"]))

    return {"months": months,
            "monthly": [{"m": m, **month_stats[m]} for m in months],
            "parties": party_series,
            "agreement": matrix(agree), "agreement12": matrix(agree12),
            "mps": mp_rows,
            "defeats": defeats[-30:][::-1],
            "totalVotes": len(votes),
            "firstVote": votes[0]["t"] if votes else None,
            "lastVote": votes[-1]["t"] if votes else None}


# ---------------------------------------------------------------- compass (MDS of vote agreement)
def popcount(x):
    return bin(x).count("1")


def top2_eigen(B, iters=300):
    n = len(B)
    vecs, vals = [], []
    for k in range(2):
        v = [math.sin(i * 1.7 + k) + 1.1 for i in range(n)]
        lam = 0.0
        for _ in range(iters):
            w = [sum(B[i][j] * v[j] for j in range(n)) for i in range(n)]
            for u, ul in zip(vecs, vals):  # deflate
                d = sum(u[i] * v[i] for i in range(n))
                w = [w[i] - ul * d * u[i] for i in range(n)]
            norm = math.sqrt(sum(x * x for x in w)) or 1.0
            lam = sum(w[i] * v[i] for i in range(n))
            v = [x / norm for x in w]
        vecs.append(v)
        vals.append(lam)
    return vecs, vals


def mds(votes, min_participation=0.25):
    """Classical MDS on pairwise disagreement rates between MPs (J/E votes only)."""
    # keep contested votes only: minority at least 10% of J+E
    contested = []
    for v in votes:
        j = sum(1 for b in v["ballots"] if b[2] == "J")
        e = sum(1 for b in v["ballots"] if b[2] == "E")
        if j + e and min(j, e) / (j + e) >= 0.10:
            contested.append(v)
    if len(contested) < 30:
        return None, len(contested)
    J, E, party, cnt = defaultdict(int), defaultdict(int), {}, defaultdict(int)
    for i, v in enumerate(contested):
        bit = 1 << i
        for hn, p, code in v["ballots"]:
            party[hn] = p
            if code == "J":
                J[hn] |= bit
                cnt[hn] += 1
            elif code == "E":
                E[hn] |= bit
                cnt[hn] += 1
    ids = [hn for hn in cnt if cnt[hn] >= min_participation * len(contested) and party[hn] in PARTIES]
    n = len(ids)
    D2 = [[0.0] * n for _ in range(n)]
    for a in range(n):
        for b in range(a + 1, n):
            x, y = ids[a], ids[b]
            same = popcount(J[x] & J[y]) + popcount(E[x] & E[y])
            diff = popcount(J[x] & E[y]) + popcount(E[x] & J[y])
            d = diff / (same + diff) if same + diff else 0.5
            D2[a][b] = D2[b][a] = d * d
    rm = [sum(r) / n for r in D2]
    gm = sum(rm) / n
    B = [[-0.5 * (D2[i][j] - rm[i] - rm[j] + gm) for j in range(n)] for i in range(n)]
    (v1, v2), (l1, l2) = top2_eigen(B)
    s1, s2 = math.sqrt(max(l1, 0)), math.sqrt(max(l2, 0))
    pts = {ids[i]: (v1[i] * s1, v2[i] * s2) for i in range(n)}
    return {"pts": pts, "party": party, "var": (l1, l2)}, len(contested)


def procrustes(src, ref):
    """Rotate/reflect src points (dict) to best match ref (dict) on common keys."""
    common = [k for k in src if k in ref]
    best = None
    for flip in (1, -1):
        num = den = 0.0
        for k in common:
            x, y = src[k][0], flip * src[k][1]
            u, w = ref[k]
            num += x * w - y * u
            den += x * u + y * w
        th = math.atan2(num, den)
        c, s = math.cos(th), math.sin(th)
        out = {k: (c * p[0] - s * flip * p[1], s * p[0] + c * flip * p[1]) for k, p in src.items()}
        err = sum((out[k][0] - ref[k][0]) ** 2 + (out[k][1] - ref[k][1]) ** 2 for k in common)
        if best is None or err < best[0]:
            best = (err, out)
    return best[1]


def defining_votes(votes, pts, dim, k=6):
    """Votes that best separate the two ends of a compass axis (point-biserial r of jaa/ei vs position)."""
    best = {}
    for v in votes:
        xs = [(pts[hn][dim], 1 if code == "J" else 0) for hn, _, code in v["ballots"]
              if code in "JE" and hn in pts]
        n = len(xs)
        j = sum(c for _, c in xs)
        if n < 50 or min(j, n - j) < 0.10 * n:
            continue
        m1 = sum(x for x, c in xs if c) / j
        m0 = sum(x for x, c in xs if not c) / (n - j)
        mean = sum(x for x, _ in xs) / n
        sd = math.sqrt(sum((x - mean) ** 2 for x, _ in xs) / n) or 1e-9
        r = (m1 - m0) / sd * math.sqrt(j * (n - j)) / n
        key = (v["item"] or v["title"]).strip().lower()
        if key not in best or abs(r) > abs(best[key]["r"]):
            best[key] = {"item": v["item"] or v["title"], "title": v["title"], "t": v["t"], "doc": v["doc"],
                         "r": r, "res": v["res"][:2]}
    top = sorted(best.values(), key=lambda x: -abs(x["r"]))[:k]
    for x in top:
        x["high"] = "J" if x["r"] > 0 else "E"  # how the high (right / top) end voted
        x["r"] = r1(x["r"], 2)
    return top


def build_compass(votes, mps):
    if not votes:
        return None
    full, n_full = mds(votes)
    pts = full["pts"]
    party_of = full["party"]

    def party_mean(points, p):
        xs = [pt for hn, pt in points.items() if party_of.get(hn) == p]
        return (sum(x for x, _ in xs) / len(xs), sum(y for _, y in xs) / len(xs)) if xs else None

    # Orientation: government to the right on axis 1; PS above VIHR on axis 2
    gx = [pts[h][0] for h in pts if party_of[h] in GOVERNMENT]
    ox = [pts[h][0] for h in pts if party_of[h] in OPPOSITION]
    sx = 1 if sum(gx) / len(gx) > sum(ox) / len(ox) else -1
    ps, vihr = party_mean(pts, "PS"), party_mean(pts, "VIHR")
    sy = 1 if ps[1] > vihr[1] else -1
    pts = {h: (sx * x, sy * y) for h, (x, y) in pts.items()}

    # Frames: rolling 12-month windows ending at each quarter end (and the latest month)
    months = sorted({v["t"][:7] for v in votes})
    ends = [m for m in months if m[5:7] in ("03", "06", "09", "12") and m >= "2023-12"]
    if months[-1] not in ends:
        ends.append(months[-1])
    frames = []
    for end in ends:
        start = month_add(end, -11)
        res, n = mds([v for v in votes if start <= v["t"][:7] <= end])
        if not res:
            continue
        aligned = procrustes(res["pts"], pts)
        party_of.update(res["party"])
        frames.append({"key": end, "label": f"{ml(max(start, months[0]))}–{ml(end)}", "votes": n,
                       "parties": {p: [r1(c, 3) for c in party_mean(aligned, p)]
                                   for p in PARTIES if party_mean(aligned, p)},
                       "mps": [[hn, r1(x, 3), r1(yv, 3)] for hn, (x, yv) in aligned.items()]})
    l1, l2 = full["var"]
    return {"full": {"votes": n_full,
                     "parties": {p: [r1(c, 3) for c in party_mean(pts, p)] for p in PARTIES if party_mean(pts, p)},
                     "mps": [[hn, mps.get(hn, hn), party_of[hn], r1(x, 3), r1(y, 3)] for hn, (x, y) in pts.items()]},
            "frames": frames, "explained": [r1(l1, 3), r1(l2, 3)],
            "defining": [defining_votes(votes, pts, 0), defining_votes(votes, pts, 1)]}


# ---------------------------------------------------------------- initiatives
def build_initiatives(items, today):
    t = today.isoformat()
    running = [x for x in items if x["state"] == "ACCEPTED" and (x["end"] or "") >= t]
    running.sort(key=lambda x: -x["support"])
    by_year = defaultdict(lambda: {"started": 0, "over50k": 0})
    for x in items:
        y = (x["start"] or "")[:4]
        if y:
            by_year[y]["started"] += 1
            if max(x["support"], x["sent"]) >= 50000:
                by_year[y]["over50k"] += 1
    year_ago = (today - datetime.timedelta(days=365)).isoformat()
    succeeded = [x for x in items if max(x["support"], x["sent"]) >= 50000 and (x["end"] or "") >= year_ago]

    def short(x):
        name = x["name"].strip()
        return {"id": x["id"], "name": name if len(name) <= 140 else name[:137].rstrip() + "…",
                "support": x["support"], "end": x["end"],
                "url": f"https://www.kansalaisaloite.fi/fi/aloite/{x['id']}"}
    return {"running": len(running), "runningOver50k": sum(1 for x in running if x["support"] >= 50000),
            "top": [short(x) for x in running[:10]],
            "succeeded12": len(succeeded), "toParliamentTotal": sum(1 for x in items if x["state"] == "DONE"),
            "byYear": [{"y": y, **by_year[y]} for y in sorted(by_year)], "total": len(items)}


def main():
    today = datetime.date.today()
    polls = build_polls(read_json(f"{CACHE}/polls.json"), today)
    elections = read_json(f"{CACHE}/elections.json")
    mps = read_json(f"{CACHE}/mps.json", {})
    votes = load_votes()
    site = {
        "updated": datetime.datetime.now(ZoneInfo("Europe/Helsinki")).strftime("%Y-%m-%d %H:%M"),
        "parties": PARTIES, "government": GOVERNMENT, "opposition": OPPOSITION,
        "polls": polls,
        "seats": build_seats(elections, polls["latest"]),
        "history": {"national": elections["national"], "governments": GOVERNMENTS,
                    "allParties": elections.get("allParties", {})},
        "parliament": build_parliament(votes, mps) if votes else None,
        "compass": build_compass(votes, mps),
        "initiatives": build_initiatives(read_json(f"{CACHE}/initiatives.json", []), today),
        "economy": read_json(f"{CACHE}/economy.json"),
        "nextElection": "2027-04-18",
    }
    write_json(f"{DATA}/site.json", site)
    print("site.json", os.path.getsize(f"{DATA}/site.json") // 1024, "KB;",
          "votes", len(votes), "; seats", site["seats"]["total"], "gov", site["seats"]["government"])


if __name__ == "__main__":
    main()
