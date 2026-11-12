#!/usr/bin/env python3
"""Build a keyword index of short excerpts from Ra, Q'uo, Latwii, Hatonn, Laitos, Oxal, L/Leema and Yadda that link back to llresearch.org.

Fair-use by design, following https://www.llresearch.org/copyright :
  * transcripts are never published: they are only kept in a private, git-ignored
    local cache (.cache/) so that rebuilds do not load llresearch.org again;
  * only short excerpts are kept (one paragraph, trimmed to MAX_CHARS), plus the
    question it answers (trimmed to MAX_Q_CHARS);
  * at most MAX_PER_SESSION excerpts are kept per session;
  * every excerpt carries credit and a deep link to the full session.

Usage: python3 build.py 1986 [1987 ...]     -> writes site/data.json
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
UA = "quo-index/0.1 (personal study index; excerpts only; github.com/meneerkrabs)"
DELAY = 1.5            # seconds between requests
MAX_CHARS = 900        # an excerpt is one paragraph, trimmed to this length
MAX_PER_SESSION = 4    # never reproduce more than this many excerpts of a session
MIN_CHARS = 200
MAX_CANDIDATES = 8     # paragraphs per session offered to the LLM judge
MIN_QUALITY = 3        # judged excerpts below this (1-5) are dropped
MAX_Q_CHARS = 400      # the question an excerpt answers is shortened to this

KEYWORDS = json.loads((Path(__file__).parent / "keywords.json").read_text())
SUBS = {k["id"]: k["subs"] for k in KEYWORDS if k.get("subs")}
KW_IDS = {k["id"] for k in KEYWORDS}
JUDGE = Path(__file__).parent / "judgments.json"      # verdicts written by judge.py
JUDGMENTS = json.loads(JUDGE.read_text()) if JUDGE.exists() else {}
OUT = Path(__file__).parent / "site" / "data.json"
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
        q = trim(" ".join(paras), MAX_Q_CHARS)
        return {"q": q, "qb": who} if q else {}
    if synopsis and not any(not source(s) for s, _, _ in turns[:i]):
        if synopsis.startswith("Topics:"):
            return {"q": trim(synopsis[7:].strip(), MAX_Q_CHARS), "qb": "Topics"}
        return {"q": trim(synopsis, MAX_Q_CHARS), "qb": "Group question"}
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
        for p in paras:
            if len(p) < MIN_CHARS:
                continue
            for kw in KEYWORDS:
                hits = len(re.findall(kw["pattern"], p, re.I))
                # a passing mention is not enough: broad words need more hits
                if hits >= kw.get("min", 2):
                    c = found.setdefault(p, {"p": p, "a": anchor, "by": src, "i": i, "kws": {}})
                    # density favours paragraphs that are really about the keyword
                    c["kws"][kw["id"]] = hits / (len(p) / 500 + 1)
    return sorted(found.values(), key=lambda c: -max(c["kws"].values()))[:MAX_CANDIDATES]


def excerpts_for(path, turns, synopsis=""):
    """Pick at most MAX_PER_SESSION paragraphs of a session and their themes."""
    cands = candidates(turns)
    judged = [c for c in cands if key_of(c["p"]) in JUDGMENTS]
    if judged:
        # An LLM read these candidates (judge.py): keep the best ones, filed under
        # the themes it found them to be about.
        for c in judged:
            j = JUDGMENTS[key_of(c["p"])]
            c["q"], c["themes"] = j["q"], [t for t in j["themes"] if t in KW_IDS]
        keep = sorted((c for c in judged if c["q"] >= MIN_QUALITY and c["themes"]),
                      key=lambda c: (-c["q"], -max(c["kws"].values())))
        chosen = [(c, c["themes"]) for c in keep[:MAX_PER_SESSION]]
    else:
        # No verdicts yet: the best paragraph per keyword, by word count.
        pairs = sorted(((s, kw, c) for c in cands for kw, s in c["kws"].items()), key=lambda x: -x[0])
        used_kw, picked = set(), {}
        for _, kw, c in pairs:
            if kw in used_kw or (id(c) not in picked and len(picked) >= MAX_PER_SESSION):
                continue
            used_kw.add(kw)
            picked.setdefault(id(c), (c, []))[1].append(kw)
        chosen = list(picked.values())
    out = []
    slug = path.replace("/channeling/", "").replace("/", "-")
    for c, kws in chosen:
        p, anchor, i = c["p"], c["a"], c["i"]
        e = {"id": f"{slug}-{anchor.strip('!')}-{key_of(p)[:6]}", "kws": [], "s": path, "a": anchor,
             "t": trim(p), "by": c["by"], **question_for(i, turns, synopsis)}
        # numbered Q&A (Ra Contact): link to "13.2" instead of the speaker turn
        num = NUMS.get(anchor) or (i and NUMS.get(turns[i - 1][1]))
        if num:
            e.update(n=num, a=num.split(".")[-1])
        for kw in kws:
            e["kws"].append(kw)
            # subcategories ("densities/third") are judged on the whole paragraph
            e["kws"] += [f"{kw}/{s['id']}" for s in SUBS.get(kw, []) if re.search(s["pattern"], p, re.I)]
        out.append(e)
    return out


def main(years):
    paths_arg = [y for y in years if y.startswith("/")]   # retry single sessions by path
    if "ra" in years:                                     # the 106 Ra Contact sessions
        paths_arg += [f"/channeling/ra-contact/{n}" for n in range(1, 107)]
    if "cache" in years:                                  # everything already cached, no network
        paths_arg = sorted("/" + "/".join(f.name[:-8].split("_", 2)) for f in CACHE.glob("*.html.gz"))
    years = [y for y in years if y.isdigit()]
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
            body = get(path, cache=True)
            title, kind, synopsis, turns = parse(body)
        except Exception as e:
            print(f"  {path}: FAILED {e}", flush=True)
            continue
        data["excerpts"] = [e for e in data["excerpts"] if e["s"] != path]
        if not any(source(s) for s, _, _ in turns):
            data["sessions"].pop(path, None)
            continue
        ex = excerpts_for(path, turns, synopsis)
        data["sessions"][path] = {"title": title, "kind": kind, "date": date_of(path, body)}
        data["excerpts"] += ex
        print(f"  {path}: {len(ex)} excerpts", flush=True)
    OUT.parent.mkdir(exist_ok=True)
    data["keywords"] = [{"id": k["id"], "label": k["label"],
                         "subs": [{"id": s["id"], "label": s["label"]} for s in k.get("subs", [])]}
                        for k in KEYWORDS]
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main(sys.argv[1:] or ["1986"])
