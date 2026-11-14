"""Shared helpers: HTTP with retries, JSON IO. Standard library only."""
import json
import os
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "cache")
UA = "Politiikkatilanne/0.1 (open data dashboard)"

# Party order and display names used everywhere.
PARTIES = ["KOK", "PS", "SDP", "KESK", "VAS", "VIHR", "RKP", "KD", "LIIK"]
GOVERNMENT = ["KOK", "PS", "RKP", "KD"]  # Orpo government, 2023–


def get(url, data=None, retries=4, timeout=60):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            if data is not None:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def get_json(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    return json.loads(get(url, data))


def write_json(path, obj, compact=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)
