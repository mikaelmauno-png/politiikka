"""Monthly economic series for Finland from Eurostat, to show alongside governments.

- Economic Sentiment Indicator (ESI): EU Commission composite of business and consumer
  confidence, seasonally adjusted, long-term average = 100 (ei_bssi_m_r2, from 1985).
- Unemployment rate, trend (une_rt_m, % of labour force, from 1988).
Output: data/cache/economy.json
"""
from common import CACHE, get_json, write_json

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
SERIES = {
    "esi": "ei_bssi_m_r2?geo=FI&indic=BS-ESI-I&s_adj=SA",
    "unemployment": "une_rt_m?geo=FI&age=TOTAL&sex=T&unit=PC_ACT&s_adj=TC",
}


def fetch(query):
    d = get_json(f"{BASE}{query}&format=JSON&lang=en")
    inv = {v: k for k, v in d["dimension"]["time"]["category"]["index"].items()}
    return sorted([inv[int(k)], v] for k, v in d["value"].items())


def main():
    out = {k: fetch(q) for k, q in SERIES.items()}
    if any(len(v) < 300 for v in out.values()):
        raise SystemExit("Eurostat returned too few observations")
    write_json(f"{CACHE}/economy.json", out)
    for k, v in out.items():
        print(k, len(v), v[0], v[-1])


if __name__ == "__main__":
    main()
