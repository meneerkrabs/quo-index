#!/usr/bin/env python3
"""Let an LLM judge the candidate excerpts: which themes each is really about and
how well it stands on its own. Verdicts go to judgments.json, which build.py uses.

Only candidate paragraphs (at most MAX_CANDIDATES per session, shortened) are sent
to the model, never whole transcripts. Reads the local cache only; no requests to
llresearch.org. Incremental: paragraphs that already have a verdict are skipped.

Usage: python3 judge.py [max_batches]
"""
import json
import re
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

import build

MODEL = "opencode-go/deepseek-v4.1-flash"
BATCH = 40
WORKERS = 8
LOCK = threading.Lock()

THEMES = "\n".join(f"{k['id']} — {k['label']}" for k in build.KEYWORDS)
PROMPT = """Do not use any tools; answer directly.

You are classifying short excerpts from the channeling transcripts of L/L Research
(sources such as Ra, Q'uo, Hatonn, Latwii) for a study index. For each excerpt decide:

- "themes": up to 5 theme ids from the list below that the excerpt is substantially
  ABOUT: it teaches or explains something on that theme. A passing mention does not
  count. Greetings and closings ("we greet you in the love and the light of the one
  infinite Creator") are not about love, light or the Creator. Use only ids from the
  list, most relevant first; [] if none fits.
- "q": 1 to 5, how valuable the excerpt is on its own. 5 = a clear, self-contained
  teaching. 3 = meaningful but leans on context. 1 = greeting, closing, housekeeping,
  talk about the channeling process itself, or a fragment.

Reply with ONLY a JSON array, one object per excerpt, in the same order, like
[{"k":"<key>","themes":["id1","id2"],"q":4}]

THEMES (id — label)
%s

EXCERPTS
%s
"""


def pending():
    items = []
    for f in sorted(build.CACHE.glob("*.html.gz")):
        path = "/" + "/".join(f.name[:-8].split("_", 2))
        _, _, synopsis, turns = build.parse(build.get(path, cache=True))
        for c in build.candidates(turns):
            k = build.key_of(c["p"])
            if k in build.JUDGMENTS:
                continue
            q = build.question_for(c["i"], turns, synopsis).get("q", "")
            items.append((k, f"[{k}] {c['by']}" + (f" (asked: {build.trim(q, 200)})" if q else "")
                          + f": {build.trim(c['p'])}"))
    return items


def judge(batch):
    prompt = PROMPT % (THEMES, "\n\n".join(text for _, text in batch))
    keys = {k for k, _ in batch}
    for _ in range(2):
        try:
            with tempfile.TemporaryDirectory() as empty:   # nothing for the agent to read
                r = subprocess.run(["opencode", "run", "-m", MODEL, prompt], cwd=empty,
                                   stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
            m = re.search(r"\[\s*\{.*\}\s*\]", r.stdout, re.S)
            rows = json.loads(m.group(0))
            good = {r["k"]: {"themes": [t for t in r["themes"] if t in build.KW_IDS][:5], "q": int(r["q"])}
                    for r in rows if r.get("k") in keys and 1 <= int(r.get("q", 0)) <= 5}
            if len(good) >= len(batch) * 0.8:
                return good
        except Exception as e:
            print("  retry:", type(e).__name__, str(e)[:80], flush=True)
    return {}


def main():
    items = pending()
    batches = [items[i:i + BATCH] for i in range(0, len(items), BATCH)]
    if len(sys.argv) > 1:
        batches = batches[:int(sys.argv[1])]
    print(f"{len(items)} paragraphs to judge, running {len(batches)} batches", flush=True)
    done = [0]

    def work(batch):
        got = judge(batch)
        with LOCK:
            build.JUDGMENTS.update(got)
            build.JUDGE.write_text(json.dumps(build.JUDGMENTS, separators=(",", ":"), sort_keys=True))
            done[0] += 1
            print(f"batch {done[0]}/{len(batches)}: {len(got)}/{len(batch)} judged", flush=True)

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, batches))


if __name__ == "__main__":
    main()
