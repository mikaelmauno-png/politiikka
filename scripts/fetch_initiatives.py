"""Citizens' initiatives from the kansalaisaloite.fi API.

Output: data/cache/initiatives.json  [{id, name, start, end, state, support, sent}]
"""
from common import CACHE, get_json, write_json

API = "https://www.kansalaisaloite.fi/api/v1/initiatives"


def main():
    out, offset = [], 0
    while True:
        batch = get_json(f"{API}?limit=50&offset={offset}")
        if not batch:
            break
        for x in batch:
            out.append({
                "id": x["id"].rsplit("/", 1)[-1],
                "name": (x.get("name") or {}).get("fi") or (x.get("name") or {}).get("sv") or "",
                "start": x.get("startDate"), "end": x.get("endDate"),
                "state": x.get("state"), "support": x.get("supportCount") or 0,
                "sent": x.get("sentSupportCount") or 0,
                "toParliament": x.get("state") == "DONE" or None,
            })
        offset += len(batch)
    write_json(f"{CACHE}/initiatives.json", out)
    states = {}
    for x in out:
        states[x["state"]] = states.get(x["state"], 0) + 1
    print(f"initiatives: {len(out)}  states: {states}")


if __name__ == "__main__":
    main()
