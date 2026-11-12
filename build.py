#!/usr/bin/env python3
"""Build a keyword index of short excerpts from Q'uo, Latwii, Hatonn, Laitos, Oxal, L/Leema and Yadda that link back to llresearch.org.

Fair-use by design, following https://www.llresearch.org/copyright :
  * transcripts are read in memory only and never written to disk;
  * only short excerpts are kept (one paragraph, trimmed to MAX_CHARS);
  * at most MAX_PER_SESSION excerpts are kept per session;
  * every excerpt carries credit and a deep link to the full session.

Usage: python3 build.py 1986 [1987 ...]     -> writes site/data.json
       python3 build.py /channeling/1990/1021  -> (re)reads single sessions
"""
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.llresearch.org"
UA = "quo-index/0.1 (personal study index; excerpts only; github.com/meneerkrabs)"
DELAY = 1.5            # seconds between requests
MAX_CHARS = 900        # an excerpt is one paragraph, trimmed to this length
MAX_PER_SESSION = 4    # never reproduce more than this many excerpts of a session
MIN_CHARS = 200

KEYWORDS = json.loads((Path(__file__).parent / "keywords.json").read_text())
OUT = Path(__file__).parent / "site" / "data.json"


def get(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace")
    time.sleep(DELAY)
    return body


def session_paths(year):
    seen, page = [], 1
    while True:
        try:
            body = get(f"/channeling/{year}/{page}")
        except Exception:
            break
        found = re.findall(rf'href="(/channeling/{year}/\d{{4}}(?:_\d+)?)"', body)
        new = [p for p in dict.fromkeys(found) if p not in seen]
        if not new:
            break
        seen += new
        page += 1
    return sorted(seen)


def text_of(fragment):
    fragment = re.sub(r"<sup\b.*?</sup>", "", fragment, flags=re.S)  # footnote refs
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def parse(body):
    """Return (title, kind, [(speaker, anchor, [paragraphs])])."""
    m = re.search(r"<title>(.*?) - L/L Research</title>", body)
    full = html.unescape(m.group(1)) if m else ""
    title, _, kind = full.partition(" - ")
    m = re.search(r'<article id="fountain">(.*?)</article>', body, re.S)
    if not m:
        return title, kind, []
    parts = re.split(
        r'<h4 class="speaker"[^>]*><span class="name" id="(![^"]+)">(.*?)</span></h4>',
        m.group(1))
    turns = []
    for i in range(1, len(parts) - 2, 3):
        anchor, speaker, chunk = parts[i], text_of(parts[i + 1]), parts[i + 2]
        paras = [text_of(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", chunk, re.S)]
        turns.append((speaker, anchor, [p for p in paras if p]))
    return title, kind, turns


def trim(p):
    if len(p) <= MAX_CHARS:
        return p
    cut = p[:MAX_CHARS]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return (cut[: end + 1] if end > MIN_CHARS else cut.rsplit(" ", 1)[0]) + " […]"


SOURCES = {"q'uo": "Q’uo", "latwii": "Latwii", "hatonn": "Hatonn",
           "laitos": "Laitos", "oxal": "Oxal", "l/leema": "L/Leema", "yadda": "Yadda"}


def source(speaker):
    """Return the canonical source name, or None for other speakers."""
    return SOURCES.get(speaker.replace("’", "'").strip().lower())


def excerpts_for(path, turns):
    """Pick the best paragraph per keyword, capped per session."""
    cands = []
    for speaker, anchor, paras in turns:
        src = source(speaker)
        if not src:
            continue
        for p in paras:
            if len(p) < MIN_CHARS:
                continue
            for kw in KEYWORDS:
                hits = len(re.findall(kw["pattern"], p, re.I))
                if hits:
                    # density favours paragraphs that are really about the keyword
                    cands.append((hits / (len(p) / 500 + 1), kw["id"], anchor, p, src))
    cands.sort(key=lambda c: -c[0])
    used_kw, picked = set(), {}   # picked: paragraph -> excerpt
    for score, kw, anchor, p, src in cands:
        if kw in used_kw:
            continue
        if p not in picked and len(picked) >= MAX_PER_SESSION:
            continue
        used_kw.add(kw)
        picked.setdefault(p, {"kws": [], "s": path, "a": anchor, "t": trim(p), "by": src})["kws"].append(kw)
    return list(picked.values())


def main(years):
    paths_arg = [y for y in years if y.startswith("/")]   # retry single sessions by path
    years = [y for y in years if not y.startswith("/")]
    data = json.loads(OUT.read_text()) if OUT.exists() else {"sessions": {}, "excerpts": []}
    for year in years:
        paths = session_paths(year)
        print(f"{year}: {len(paths)} sessions", flush=True)
        process(data, paths)
    if paths_arg:
        process(data, paths_arg)


def process(data, paths):
    for path in paths:
        try:
            title, kind, turns = parse(get(path))
        except Exception as e:
            print(f"  {path}: FAILED {e}", flush=True)
            continue
        data["excerpts"] = [e for e in data["excerpts"] if e["s"] != path]
        if not any(source(s) for s, _, _ in turns):
            data["sessions"].pop(path, None)
            continue
        ex = excerpts_for(path, turns)
        y, md = path.split("/")[2:4]
        data["sessions"][path] = {"title": title, "kind": kind, "date": f"{y}-{md[:2]}-{md[2:4]}"}
        data["excerpts"] += ex
        print(f"  {path}: {len(ex)} excerpts", flush=True)
    OUT.parent.mkdir(exist_ok=True)
    data["keywords"] = [{"id": k["id"], "label": k["label"]} for k in KEYWORDS]
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main(sys.argv[1:] or ["1986"])
