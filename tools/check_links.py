#!/usr/bin/env python3
"""Check that the source links in data/games.js still work.

Fails only for links that are clearly dead (404/410, unknown domain, no connection).
Sites that block automated checks (403, 429, 5xx) are listed as warnings.
Usage: python3 tools/check_links.py
"""
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "games.js"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def links():
    data = json.loads(DATA.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))
    found = {}
    for g in data["games"]:
        urls = [g.get("url")] + [h.get("url") for h in g["history"]]
        urls += [n.get("url") for p in g["platforms"].values() for n in p["notes"]]
        for u in urls:
            if u and u.startswith(("http://", "https://")):
                found.setdefault(u, g["name"])
    return found


def check(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            resp.read(1024)
            return url, resp.status
    except urllib.error.HTTPError as err:
        return url, err.code
    except Exception as err:  # DNS failure, refused connection, timeout, bad TLS
        return url, f"{type(err).__name__}: {err}"


def main():
    found = links()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check, found))
    dead = [(u, s) for u, s in results if s in (404, 410) or (isinstance(s, str) and "timed out" not in s)]
    unsure = [(u, s) for u, s in results if (u, s) not in dead and s != 200 and not (isinstance(s, int) and s < 400)]
    for u, s in unsure:
        print(f"warning  {s}  {found[u]}: {u}")
    for u, s in dead:
        print(f"DEAD     {s}  {found[u]}: {u}")
    print(f"\n{len(found)} links checked, {len(dead)} dead, {len(unsure)} couldn't be checked.")
    sys.exit(1 if dead else 0)


if __name__ == "__main__":
    main()
