#!/usr/bin/env python3
"""Build the Love/Light Index: the text of the L/L Research channelings, session by
session and by theme, each piece with credit and a link to its original page.

Every session is kept whole. Each speaker turn becomes one or more pieces (only a very
long turn is split, and only at paragraph or sentence ends), and no text is ever
shortened, reworded or left out. Pieces are filed under up to MAX_THEMES themes, taken
from an LLM's reading of the candidates (judge.py) or, where it has no verdict, from the
patterns in keywords.json.

A private, git-ignored cache of the pages (.cache/) makes rebuilds cheap and keeps the
load on llresearch.org to one visit per page.

Output in site/:
  index.json   keywords with counts, sessions (title, date, speakers): the first thing the
               site loads, and all it needs for the keyword and session lists
  corpus.json  every piece of text, in session order: loaded once, on demand, for keyword
               pages, sessions, search and permalinks

Usage: python3 build.py 1986 [1987 ...]     -> rebuild those years
       python3 build.py ra                     -> the Ra Contact sessions
       python3 build.py cache                  -> rebuild from the local cache, no network
       python3 build.py /channeling/1990/1021  -> (re)reads single sessions
"""
import gzip
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.llresearch.org"
UA = "quo-index/0.1 (personal study index; github.com/meneerkrabs)"
DELAY = 1.5            # seconds between requests
MAX_PIECE = 3000       # a piece of one speaker turn is at most this many characters
MAX_THEMES = 3         # themes filed per piece, most relevant first
MAX_ATTACHED_Q = 1500  # the question shown above a piece (it is also in the session itself)
MIN_CHARS = 200        # candidates() below only offers paragraphs at least this long
MAX_CANDIDATES = 8     # paragraphs per session offered to the LLM judge
MAX_QUALITY = 5        # a judge verdict is 1-5
MIN_QUALITY = 3        # verdicts below this do not add a theme
MAX_CHARS = 1500       # trim() default; judge.py sends shortened candidates

KEYWORDS = json.loads((Path(__file__).parent / "keywords.json").read_text())
SUBS = {k["id"]: k["subs"] for k in KEYWORDS if k.get("subs")}
KW_IDS = {k["id"] for k in KEYWORDS}
JUDGE = Path(__file__).parent / "judgments.json"      # verdicts written by judge.py
JUDGMENTS = json.loads(JUDGE.read_text()) if JUDGE.exists() else {}
SITE = Path(__file__).parent / "site"
INDEX = SITE / "index.json"
CORPUS2 = SITE / "corpus.json"
CACHE = Path(__file__).parent / ".cache"   # private, git-ignored


def get(path, cache=False):
    """Fetch a page. Session pages are kept in a private local cache (never
    committed or published) so that rebuilds do not hit llresearch.org again."""
    f = CACHE / (path.strip("/").replace("/", "_") + ".html.gz")
    if cache and f.exists():
        return gzip.decompress(f.read_bytes()).decode("utf-8")
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace")
    time.sleep(DELAY)
    if cache:
        CACHE.mkdir(exist_ok=True)
        f.write_bytes(gzip.compress(body.encode("utf-8")))
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
    """Return (title, kind, synopsis, [(speaker, anchor, [paragraphs])])."""
    NUMS.clear()
    m = re.search(r"<title>(.*?) - L/L Research</title>", body)
    full = html.unescape(m.group(1)) if m else ""
    title, _, kind = full.partition(" - ")
    m = re.search(r'<article id="fountain">(.*?)</article>', body, re.S)
    if not m:
        return title, kind, "", []
    syn = re.search(r'<p class="hint-content">(.*?)</p>', m.group(1), re.S)
    synopsis = text_of(syn.group(1)) if syn else ""
    # Ra Contact pages number their questions: <a class="num" href="#2">13.2</a>
    parts = re.split(
        r'<h4 class="speaker"[^>]*>(?:<a class="num"[^>]*>([\d.]+)</a>)?'
        r'<span class="name" id="(![^"]+)">(.*?)</span></h4>',
        m.group(1))
    turns = []
    for i in range(1, len(parts) - 3, 4):
        num, anchor, speaker, chunk = parts[i], parts[i + 1], text_of(parts[i + 2]), parts[i + 3]
        paras = [text_of(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", chunk, re.S)]
        turns.append((speaker, anchor, [p for p in paras if p]))
        if num:
            NUMS[anchor] = num
    return title, kind, synopsis, turns


MONTHS = ("January February March April May June July August September October "
          "November December").split()


def date_of(path, body):
    """Sessions are /channeling/YYYY/MMDD; Ra Contact pages print their date."""
    y, md = path.split("/")[2:4]
    if y.isdigit():
        return f"{y}-{md[:2]}-{md[2:4]}"
    m = re.search(rf"({'|'.join(MONTHS)}) (\d{{1,2}}), (\d{{4}})", body)
    return f"{m.group(3)}-{MONTHS.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}" if m else ""


def trim(p, limit=MAX_CHARS):
    """Shorten a paragraph to limit characters (judge.py sends shortened candidates)."""
    if len(p) <= limit:
        return p
    cut = p[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return (cut[: end + 1] if end > MIN_CHARS else cut.rsplit(" ", 1)[0]) + " […]"


NUMS = {}   # anchor -> question number ("13.2") of the page being parsed
SOURCES = {"ra": "Ra", "q'uo": "Q’uo", "latwii": "Latwii", "hatonn": "Hatonn",
           "laitos": "Laitos", "oxal": "Oxal", "l/leema": "L/Leema", "yadda": "Yadda",
           "yom": "Yom", "quanta": "Quanta", "halos": "Halos", "biondha": "Biondha",
           "tovo": "Tovo", "monka": "Monka"}


def source(speaker):
    """Return the canonical source name, or None for other speakers."""
    return SOURCES.get(speaker.replace("’", "'").strip(" *").lower())


def question_for(i, turns, synopsis):
    """The question a turn answers: the questioner's turn just before it, or, for
    the opening message, the group question or topic line of the session."""
    if i and not source(turns[i - 1][0]):
        who, _, paras = turns[i - 1]
        q = " ".join(paras)
        return {"q": q, "qb": who} if q else {}
    if synopsis and not any(not source(s) for s, _, _ in turns[:i]):
        if synopsis.startswith("Topics:"):
            return {"q": synopsis[7:].strip(), "qb": "Topics"}
        return {"q": synopsis, "qb": "Group question"}
    return {}


def key_of(p):
    return hashlib.sha1(p.encode()).hexdigest()[:12]


def candidates(turns):
    """The MAX_CANDIDATES most keyword-dense paragraphs of a session, best first."""
    found = {}
    for i, (speaker, anchor, paras) in enumerate(turns):
        src = source(speaker)
        if not src:
            continue
        for j, p in enumerate(paras):
            if len(p) < MIN_CHARS:
                continue
            for kw in KEYWORDS:
                hits = len(re.findall(kw["pattern"], p, re.I))
                # a passing mention is not enough: broad words need more hits
                if hits >= kw.get("min", 2):
                    c = found.setdefault(p, {"p": p, "a": anchor, "by": src, "i": i, "j": j, "kws": {}})
                    # density favours paragraphs that are really about the keyword
                    c["kws"][kw["id"]] = hits / (len(p) / 500 + 1)
    return sorted(found.values(), key=lambda c: -max(c["kws"].values()))[:MAX_CANDIDATES]


def split_long(p, limit=MAX_PIECE):
    """Split one overlong paragraph at sentence ends (at a space as a last resort).
    Nothing is added, cut off or changed: the pieces follow each other exactly."""
    out, rest = [], p
    while len(rest) > limit:
        cut = rest[:limit]
        end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
        if end < limit // 2:
            end = cut.rfind(" ")
        if end <= 0:
            end = limit
        out.append(rest[: end + 1].strip())
        rest = rest[end + 1:].strip()
    if rest:
        out.append(rest)
    return out


def grouped(paras):
    """A turn's paragraphs grouped into pieces of at most MAX_PIECE characters, split
    only at paragraph or sentence ends. Returns [(text, [paragraphs in it])]."""
    out, cur, curp = [], "", []
    for p in paras:
        for piece in split_long(p):
            if cur and len(cur) + 2 + len(piece) > MAX_PIECE:
                out.append((cur, curp))
                cur, curp = piece, [p]
            else:
                cur = cur + "\n\n" + piece if cur else piece
                curp.append(p)
    if cur:
        out.append((cur, curp))
    return out


def density(pattern, text):
    """How much of a text is about a pattern: hits weighted down by its length."""
    return 3 * len(re.findall(pattern, text, re.I)) / (len(text) / 500 + 1)


def themes_of(text, paras):
    """The themes a piece is filed under, with how strongly: what an LLM judge saw in it,
    topped up with the keyword patterns. The score says how much of the piece is about the
    theme, not how long the piece is, so a long passage that passes a theme in one
    paragraph does not outrank a short one that is entirely about it."""
    score = {}
    for p in paras:
        j = JUDGMENTS.get(key_of(p))
        if j and j.get("q", 0) >= MIN_QUALITY:
            for t in j.get("themes", []):
                if t in KW_IDS:
                    score[t] = score.get(t, 0) + 2 * j["q"]
    for t in score:
        score[t] /= max(1, len(paras))      # the judge's verdict, averaged over the piece
    for kw in KEYWORDS:
        if len(re.findall(kw["pattern"], text, re.I)) >= kw.get("min", 2):
            score[kw["id"]] = score.get(kw["id"], 0) + density(kw["pattern"], text)
    best = sorted(score, key=lambda k: (-score[k], k))[:MAX_THEMES]
    kws = []
    for kw in best:
        kws.append((kw, score[kw]))
        for s in SUBS.get(kw, []):
            # a subcategory is sorted on its own presence, plus the theme's strength
            if re.search(s["pattern"], text, re.I):
                kws.append((f"{kw}/{s['id']}", score[kw] + density(s["pattern"], text)))
    return kws


def excerpts_for(path, turns, synopsis=""):
    """Every word of the session, in order, as pieces that link back to their turn."""
    out = []
    slug = path.replace("/channeling/", "").replace("/", "-")
    for i, (speaker, anchor, paras) in enumerate(turns):
        if not paras:
            continue
        src = source(speaker)
        num = NUMS.get(anchor) or (i and NUMS.get(turns[i - 1][1]))
        for k, (text, plist) in enumerate(grouped(paras), 1):
            themed = themes_of(text, plist) if src else []
            e = {"id": f"{slug}-{anchor.strip('!')}-{k}", "kws": [t for t, _ in themed],
                 "s": path, "a": anchor, "t": text, "by": src or speaker}
            if themed:
                # how strongly the piece belongs to each theme; the site sorts pages on it
                e["w"] = {t: round(s, 1) for t, s in themed}
            if src:
                e["r"] = 1
                if k == 1:
                    q = question_for(i, turns, synopsis)
                    if q and len(q["q"]) <= MAX_ATTACHED_Q:
                        e.update(q)
            # numbered Q&A (Ra Contact): link to "13.2" instead of the speaker turn
            if num:
                e.update(n=num, a=num.split(".")[-1])
            out.append(e)
    return out


def load():
    """Everything built before, so that a rebuild of a few sessions keeps the rest."""
    data = {"sessions": {}, "excerpts": {}}
    if INDEX.exists():
        data["sessions"] = json.loads(INDEX.read_text())["sessions"]
    if CORPUS2.exists():
        for e in json.loads(CORPUS2.read_text())["excerpts"]:
            data["excerpts"].setdefault(e["s"], []).append(e)
    return data


def write(data):
    sessions = data["sessions"]
    order = sorted(sessions, key=lambda p: (sessions[p]["date"], p))
    exs = [e for p in order for e in data["excerpts"].get(p, [])]
    counts = {}
    for e in exs:
        for k in e["kws"]:
            counts[k] = counts.get(k, 0) + 1
    sources = {}
    for e in exs:
        if e.get("r"):
            sources[e["by"]] = sources.get(e["by"], 0) + 1
    years = sorted({sessions[p]["date"][:4] for p in sessions if sessions[p]["date"]})
    index = {
        "keywords": [{"id": k["id"], "label": k["label"], "n": counts.get(k["id"], 0),
                      "subs": [{"id": s["id"], "label": s["label"], "n": counts.get(f"{k['id']}/{s['id']}", 0)}
                               for s in k.get("subs", [])]}
                     for k in KEYWORDS],
        "sessions": {p: sessions[p] for p in order},
        "sources": sources,
        "years": years,
        "total": len(exs),
        "built": int(time.time()),   # the site asks for corpus.json?<built>, so it can be cached
    }
    SITE.mkdir(exist_ok=True)
    INDEX.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
    CORPUS2.write_text(json.dumps({"excerpts": exs}, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(exs)} pieces from {len(sessions)} sessions, "
          f"{sum(len(e['t']) for e in exs)} characters", flush=True)


def process(data, paths):
    for path in paths:
        try:
            body = get(path, cache=True)
            title, kind, synopsis, turns = parse(body)
        except Exception as e:
            print(f"  {path}: FAILED {e}", flush=True)
            continue
        data["excerpts"].pop(path, None)
        if not any(source(s) for s, _, _ in turns):
            data["sessions"].pop(path, None)
            continue
        ex = excerpts_for(path, turns, synopsis)
        data["sessions"][path] = {"title": title, "kind": kind, "date": date_of(path, body),
                                  "n": len(ex), "by": sorted({e["by"] for e in ex if e.get("r")})}
        data["excerpts"][path] = ex
        print(f"  {path}: {len(ex)} pieces", flush=True)
    write(data)


def main(years):
    paths_arg = [y for y in years if y.startswith("/")]   # retry single sessions by path
    if "ra" in years:                                     # the 106 Ra Contact sessions
        paths_arg += [f"/channeling/ra-contact/{n}" for n in range(1, 107)]
    if "cache" in years:                                  # everything already cached, no network
        paths_arg = sorted("/" + "/".join(f.name[:-8].split("_", 2)) for f in CACHE.glob("*.html.gz"))
    years = [y for y in years if y.isdigit()]
    data = load()
    for year in years:
        paths = session_paths(year)
        print(f"{year}: {len(paths)} sessions", flush=True)
        process(data, paths)
    if paths_arg:
        process(data, paths_arg)
    if not years and not paths_arg:
        write(data)


if __name__ == "__main__":
    main(sys.argv[1:] or ["1986"])
