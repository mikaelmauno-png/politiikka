"""Parliamentary election results from Statistics Finland (StatFin PxWeb).

Output: data/cache/elections.json
  national:  {year: {party: share%}}          1983–2023
  districts: {VPxx: {name, seats, votes: {party: votes}}}  2023
"""
from common import CACHE, PARTIES, get_json, write_json

BASE = "https://pxdata.stat.fi/PXWeb/api/v1/fi/StatFin/evaa/"
CODE2PARTY = {"03": "KOK", "02": "PS", "01": "SDP", "04": "KESK", "05": "VIHR",
              "06": "VAS", "07": "RKP", "08": "KD", "09": "LIIK"}


def query(table, selections):
    payload = {"query": [{"code": c, "selection": {"filter": "item", "values": v}}
                         for c, v in selections.items()],
               "response": {"format": "json-stat2"}}
    return get_json(BASE + table, payload)


def cells(js):
    """Yield (dict of dim->code, value) from a json-stat2 response."""
    dims = js["id"]
    sizes = js["size"]
    idx = {d: sorted(js["dimension"][d]["category"]["index"].items(), key=lambda kv: kv[1])
           for d in dims}
    for flat, val in enumerate(js["value"]):
        rem, pos = flat, {}
        for d, s in reversed(list(zip(dims, sizes))):
            pos[d] = idx[d][rem % s][0]
            rem //= s
        yield pos, val


def main():
    meta = get_json(BASE + "13sw.px")
    var = {v["code"]: v for v in meta["variables"]}
    years = var["timeperiod_y"]["values"]
    area = var["kunta_109_20230101"]
    districts = [(c, t) for c, t in zip(area["values"], area["valueTexts"]) if t.startswith("VP")]

    # National share history
    js = query("13sw.px", {"timeperiod_y": years, "sukupuoli_9_20180101": ["SSS"],
                           "puolue_19_20230101": list(CODE2PARTY), "kunta_109_20230101": ["SSS"],
                           "contentscode": ["evaa_osuus_aanista"]})
    national = {}
    for pos, val in cells(js):
        if val is None:
            continue
        national.setdefault(pos["timeperiod_y"], {})[CODE2PARTY[pos["puolue_19_20230101"]]] = val

    # 2023 votes by district (parties + total, so "others" can be derived)
    js = query("13sw.px", {"timeperiod_y": ["2023"], "sukupuoli_9_20180101": ["SSS"],
                           "puolue_19_20230101": ["SSS"] + list(CODE2PARTY),
                           "kunta_109_20230101": [c for c, _ in districts],
                           "contentscode": ["evaa_aanet"]})
    dvotes = {}
    for pos, val in cells(js):
        p = pos["puolue_19_20230101"]
        dvotes.setdefault(pos["kunta_109_20230101"], {})[CODE2PARTY.get(p, "TOTAL")] = val or 0

    # Seats per district 2023
    js = query("13t4.px", {"timeperiod_y": ["2023"], "sukupuoli_9_20180101": ["SSS"],
                           "puolue_4_20230303": ["SSS"], "Ikä": ["SSS"],
                           "aanestysalue_26_20230101": ["VP%02d" % i for i in range(1, 14)]})
    seats = {pos["aanestysalue_26_20230101"]: int(val) for pos, val in cells(js)}

    # Every party that has fielded candidates since 1983 (national votes and share)
    party_var = var["puolue_19_20230101"]
    names = dict(zip(party_var["values"], party_var["valueTexts"]))
    codes = [c for c in party_var["values"] if c != "SSS"]
    js = query("13sw.px", {"timeperiod_y": years, "sukupuoli_9_20180101": ["SSS"],
                           "puolue_19_20230101": codes, "kunta_109_20230101": ["SSS"],
                           "contentscode": ["evaa_aanet", "evaa_osuus_aanista"]})
    all_parties = {}
    for pos, val in cells(js):
        if not val:
            continue
        c = pos["puolue_19_20230101"]
        rec = all_parties.setdefault(c, {"abbr": CODE2PARTY.get(c, names[c]), "votes": {}, "share": {}})
        key = "votes" if pos["contentscode"] == "evaa_aanet" else "share"
        rec[key][pos["timeperiod_y"]] = val

    out = {}
    for code, text in districts:
        vp = text.split()[0]
        if vp not in seats:  # pre-2013 districts (Kymi, Etelä-Savo, ...)
            continue
        out[vp] = {"name": text.split(" ", 1)[1].replace(" vaalipiiri", ""),
                   "seats": seats.get(vp), "votes": dvotes[code]}
    write_json(f"{CACHE}/elections.json", {"national": national, "districts": out,
                                           "allParties": all_parties}, compact=False)
    print("years", sorted(national), "seat total", sum(seats.values()))
    print("2023", national.get("2023"))
    print("all parties", len(all_parties))


if __name__ == "__main__":
    main()
