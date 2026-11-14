# Politiikkatilanne

Suomen poliittinen tilanne avoimista tilastoista, Suhdannetilanne.fi:n hengessä.
Staattinen sivu (`index.html`, `app.js`, `style.css`), joka lukee yhden tiedoston `data/site.json`.

## Osiot
- **Tilanne**: hallituspuolueiden kannatusvaihe (nousu / hidastuminen / lasku / elpyminen)
- **Kannatuskartta**: puolueet tason (ero vuoden 2023 vaaleihin) ja 3 kk muutoksen nelikentässä, aikaliukuri
- **Paikkaennuste**: mittausten keskiarvo → vaalipiirikohtainen d'Hondt
- **Eduskunta**: ryhmien yhtenäisyys, läsnäolo, hallituksen tappiot, ryhmien samanlaisuus, linjasta poikkeajat
- **Nelikenttä**: edustajien sijainti äänestyskäyttäytymisen perusteella (MDS), kausittain
- **Kansalaisaloitteet** ja **historia** (talous ja hallitukset 1985–, vaalitulokset 1983–2023, hallitukset)

## Data
| Skripti | Lähde | Välimuisti |
|---|---|---|
| `scripts/fetch_polls.py` | Wikipedian mittaustaulukko (Yle/Taloustutkimus, HS/Verian…) | `data/cache/polls.json` |
| `scripts/fetch_elections.py` | Tilastokeskus StatFin | `data/cache/elections.json` |
| `scripts/fetch_votes.py` | Eduskunnan avoin data (inkrementaalinen) | `data/cache/votes.jsonl`, `mps.json` |
| `scripts/fetch_initiatives.py` | kansalaisaloite.fi | `data/cache/initiatives.json` |
| `scripts/fetch_economy.py` | Eurostat: luottamusindikaattori (ESI) ja työttömyysaste | `data/cache/economy.json` |
| `scripts/build.py` | kaikki yllä | `data/site.json` |

Vain Pythonin standardikirjasto. GitHub Actions (`.github/workflows/update.yml`) ajaa kaiken kerran vuorokaudessa ja committaa muuttuneen datan.

Paikallisesti:
```
cd scripts && python3 fetch_polls.py && python3 fetch_elections.py && python3 fetch_votes.py && python3 fetch_initiatives.py && python3 build.py
cd .. && python3 -m http.server 8791
```

Hallituskokoonpano on `scripts/common.py`:n `GOVERNMENT`-listassa – päivitä, jos hallitus vaihtuu.
