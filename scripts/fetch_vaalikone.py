"""Party positions on left–right and liberal–conservative axes from Yle's election-compass open data.

Source: Yle open data (CC BY), candidates' anonymised answers. https://yle.fi/a/20-10006887
The statements per axis are defined in vaalikone_scales.py.

A candidate's position on an axis = mean of their answers on that axis's statements, each answer
mapped 1..5 -> -1..+1 and flipped for statements where agreeing means left/liberal.
At least 60 % of an axis's statements must be answered. A party's position = mean of its candidates;
the spread is the 25–75 % range of its candidates.

Historical files never change, so they are downloaded only when the cache lacks an election
(use --force to rebuild). Output: data/cache/vaalikone.json
"""
import csv
import io
import statistics
import sys
import urllib.request
import zipfile

from common import CACHE, UA, read_json, write_json
from vaalikone_scales import ELECTIONS, PARTY_ALIASES

OUT = f"{CACHE}/vaalikone.json"
REGIONS_2025 = ["ita-uudenmaan", "keski-uudenmaan", "lansi-uudenmaan", "vantaan_ja_keravan", "varsinais-suomen",
                "satakunnan", "kanta-hameen", "pirkanmaan", "paijat-hameen", "kymenlaakson", "etela-karjalan",
                "etela-savon", "pohjois-savon", "pohjois-karjalan", "keski-suomen", "etela-pohjanmaan", "pohjanmaan",
                "keski-pohjanmaan", "pohjois-pohjanmaan", "kainuun", "lapin"]
MIN_CANDIDATES = 15


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def rows_from_csv(text):
    """-> (header list, list of row lists)"""
    rows = list(csv.reader(io.StringIO(text)))
    return [h.strip() for h in rows[0]], rows[1:]


def load(key):
    """Return (statement_texts, candidates) where candidates = [(party_name, {statement: answer_str})]."""
    if key == "e2019":
        z = zipfile.ZipFile(io.BytesIO(download("https://vaalit.beta.yle.fi/avoindata/avoin_data_eduskuntavaalit_2019.zip")))
        name = next(n for n in z.namelist() if n.endswith(".csv") and not n.startswith("__MACOSX"))
        tables = [rows_from_csv(z.read(name).decode("utf-8-sig"))]
    elif key == "e2023":
        tables = [rows_from_csv(download("https://old-vaalikone.yle.fi/vaalikone/eduskuntavaalit2023/"
                                         "Eduskuntavaalit%202023%20vastausdata%20-%20Kaikki%20vaalipiirit%20-%20anonyymi.csv")
                                .decode("utf-8-sig"))]
    elif key == "a2025":
        tables = [rows_from_csv(download(f"https://vaalit.yle.fi/avoindata/av2025/{i}_{n}_hyvinvointialue.csv")
                                .decode("utf-8-sig")) for i, n in enumerate(REGIONS_2025, 1)]
    elif key == "k2021":
        base = "https://vaalit.beta.yle.fi/avoindata/Kuntavaalit2021_avoindata"
        qs = {r["id"]: r["text_fi"].strip() for r in csv.DictReader(io.StringIO(download(base + "_kysymykset.csv").decode("utf-8-sig")))}
        ps = {r["id"]: r["name_fi"].strip() for r in csv.DictReader(io.StringIO(download(base + "_puolueet.csv").decode("utf-8-sig")))}
        cands = []
        for r in csv.DictReader(io.StringIO(download(base + ".csv").decode("utf-8-sig"))):
            cands.append((ps.get(r["party_id"], ""), {qs[k[1:-7]]: v for k, v in r.items()
                                                       if k.startswith("q") and k.endswith(".answer") and k[1:-7] in qs}))
        return list(qs.values()), cands
    else:
        raise ValueError(key)
    statements, cands = None, []
    for header, rows in tables:
        # columns: vaalipiiri, puolue, [valintatieto], statements..., then repeated statements with comments
        first = {}
        for i, h in enumerate(header):
            if i >= 2 and h not in first:
                first[h] = i
        statements = statements or list(first)
        for r in rows:
            if len(r) > 1:
                cands.append((r[1].strip(), {h: r[i] for h, i in first.items() if i < len(r)}))
    return statements, cands


def match(statements, prefix):
    hits = [s for s in statements if s.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"Statement prefix matched {len(hits)} columns: {prefix!r}")
    return hits[0]


def answer(v):
    v = (v or "").strip()
    return (int(v) - 3) / 2 if v in ("1", "2", "3", "4", "5") else None


def axis_score(ans, items):
    vals = [answer(ans.get(s)) for s, _ in items]
    got = [v * d for v, (_, d) in zip(vals, items) if v is not None]
    return sum(got) / len(got) if len(got) >= 0.6 * len(items) else None


def q(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def build(e):
    statements, cands = load(e["key"])
    axes = {ax: [(match(statements, pre), d) for pre, d in e[ax]] for ax in ("economy", "values")}
    by_party = {}
    for party, ans in cands:
        x, y = axis_score(ans, axes["economy"]), axis_score(ans, axes["values"])
        if x is None or y is None or not party:
            continue
        by_party.setdefault(PARTY_ALIASES.get(party, party), []).append((x, y))
    parties = {}
    for p, pts in by_party.items():
        if len(pts) < MIN_CANDIDATES:
            continue
        xs, ys = [a for a, _ in pts], [b for _, b in pts]
        parties[p] = {"n": len(pts), "x": round(statistics.mean(xs), 3), "y": round(statistics.mean(ys), 3),
                      "x25": round(q(xs, .25), 3), "x75": round(q(xs, .75), 3),
                      "y25": round(q(ys, .25), 3), "y75": round(q(ys, .75), 3)}
    n = sum(len(v) for v in by_party.values())
    print(f"{e['key']}: {len(cands)} candidates, {n} scored, {len(parties)} parties")
    return {"key": e["key"], "label": e["label"], "short": e["short"], "date": e["date"], "candidates": n,
            "statements": {ax: [{"text": s, "dir": d} for s, d in items] for ax, items in axes.items()},
            "parties": parties}


def main():
    force = "--force" in sys.argv
    cached = read_json(OUT, {"elections": []})
    have = {e["key"]: e for e in cached["elections"]}
    out = []
    for e in ELECTIONS:
        # rebuild when forced, missing, or when the statement definitions changed
        defs = {ax: [list(t) for t in e[ax]] for ax in ("economy", "values")}
        old = have.get(e["key"])
        if not force and old and old.get("defs") == defs:
            out.append(old)
            continue
        res = build(e)
        res["defs"] = defs
        out.append(res)
    write_json(OUT, {"source": "https://yle.fi/a/20-10006887", "elections": out}, compact=False)


if __name__ == "__main__":
    main()
