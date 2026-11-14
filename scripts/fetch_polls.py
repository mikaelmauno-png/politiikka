"""Parse national opinion polls from the Wikipedia poll page (wikitext).

Output: data/cache/polls.json  ->  [{date, firm, n, KOK, PS, ...}], newest first,
plus the 2023 election row as {"election": {...}}.
"""
import json
import re
import urllib.parse

from common import CACHE, PARTIES, get, write_json

PAGE = "Opinion_polling_for_the_2027_Finnish_parliamentary_election"
URL = ("https://en.wikipedia.org/w/api.php?action=parse&prop=wikitext&format=json"
       "&formatversion=2&page=" + urllib.parse.quote(PAGE))

# Column order in the tables: KOK PS SDP KESK VAS VIHR SFP(=RKP) KD LIIK
TABLE_PARTIES = ["KOK", "PS", "SDP", "KESK", "VAS", "VIHR", "RKP", "KD", "LIIK"]


def clean(cell):
    cell = re.sub(r"<ref[^>]*/>", "", cell)
    cell = re.sub(r"<ref[^>]*>.*?</ref>", "", cell, flags=re.S)
    # "style=... | value": keep part after the last top-level pipe
    depth, cut = 0, -1
    for i, ch in enumerate(cell):
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "|" and depth == 0:
            cut = i
    if cut >= 0:
        cell = cell[cut + 1:]
    cell = cell.replace("'''", "").replace("''", "")
    cell = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", cell)
    return cell.strip()


def num(s):
    s = s.replace(",", "").replace("–", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse(wikitext):
    # National section only (stop at sub-national polls)
    end = wikitext.find("== Sub-national")
    text = wikitext[:end if end > 0 else None]
    polls, election = [], None
    for table in re.findall(r"\{\|.*?\n\|\}", text, flags=re.S):
        for row in table.split("\n|-")[1:]:
            lines = [l for l in row.split("\n") if l.startswith("|") and not l.startswith("|}")]
            if len(lines) < 3 + len(TABLE_PARTIES):
                continue
            date_m = re.search(r'data-sort-value="\s*(\d{4}-\d{2}-\d{2})', lines[0])
            if not date_m:
                continue
            cells = [clean(l[1:]) for l in lines]
            firm, n = cells[1], num(cells[2])
            vals = [num(c) for c in cells[3:3 + len(TABLE_PARTIES)]]
            if any(v is None for v in vals) or not (90 < sum(vals) <= 101):
                continue
            rec = {"date": date_m.group(1), "firm": firm, "n": n}
            rec.update(dict(zip(TABLE_PARTIES, vals)))
            if "election" in firm.lower():
                election = rec
            else:
                polls.append(rec)
    polls.sort(key=lambda p: p["date"], reverse=True)
    return polls, election


def main():
    wt = json.loads(get(URL))["parse"]["wikitext"]
    polls, election = parse(wt)
    if len(polls) < 20:
        raise SystemExit(f"Only {len(polls)} polls parsed; page layout changed?")
    write_json(f"{CACHE}/polls.json", {"source": "https://en.wikipedia.org/wiki/" + PAGE,
                                       "election2023": election, "polls": polls}, compact=False)
    firms = sorted({p["firm"] for p in polls})
    print(f"polls: {len(polls)} ({polls[-1]['date']} .. {polls[0]['date']}), firms: {firms}")


if __name__ == "__main__":
    main()
