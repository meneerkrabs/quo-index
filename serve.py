#!/usr/bin/env python3
"""Local server for the site plus "the noble helper", an LLM guide to the excerpts.

LOCAL, PERSONAL USE ONLY. The helper reads L/L Research excerpts in order to explain
them. L/L Research's copyright policy requires their written permission for any
public tool that retrieves their content, so this is not deployed with the public
site; the site only shows the helper when this server answers at /api/guide.

Usage: python3 serve.py [port]      (needs the `opencode` CLI)
"""
import json
import re
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent / "site"
MODEL = "opencode-go/deepseek-v4.1-flash"
MAX_EXCERPTS = 6
STOP = set("""the and for that this with what does about are how why from have has was were which when
who whom you your can could would should there their them they will into than then been being not but
een het de van en is wat hoe waarom over met voor dat die zijn niet maar ook kan wil mij mijn naar""".split())

PROMPT = """Do not use any tools; answer directly.

You are "the noble helper": a scribe of ancient Egypt, drawn as a small figure on a study
site with excerpts from the channelings of L/L Research. You help a reader understand the
excerpts below. Rules you never break:
- You are not Ra, Q'uo or any channeled source, and you never speak as one or imitate
  their voice. You are a fellow student. A light Egyptian touch is fine; no role-play of
  the sources.
- You do not claim that anything in the excerpts is true. Report it as what the source
  says ("Q'uo says…", "in this excerpt Ra describes…").
- Stay with the excerpts. Cite them as [1], [2]. If they do not answer the question, say
  so plainly instead of filling in from elsewhere.
- Explain in plain words; unpack the jargon. At most about 180 words.
- Answer in the language of the reader's question.
- End with one short sentence reminding the reader that you are a language model that
  can be wrong, and that the excerpts should be read in their full session.

EXCERPTS
%s

EARLIER IN THIS CONVERSATION
%s

READER'S QUESTION
%s
"""


def load():
    d = json.loads((ROOT / "data.json").read_text())
    return d, {e["id"]: e for e in d["excerpts"]}


def find(question, ids, by_id, data):
    """The excerpts the reader pointed at, topped up with a plain word search."""
    picked = [by_id[i] for i in ids if i in by_id][:MAX_EXCERPTS]
    words = {w for w in re.findall(r"[a-zà-ÿ']{4,}", question.lower()) if w not in STOP}
    if words and len(picked) < MAX_EXCERPTS:
        def score(e):
            text = (e["t"] + " " + e.get("q", "")).lower()
            return sum(text.count(w) for w in words) + 3 * sum(w in " ".join(e["kws"]) for w in words)
        ranked = sorted(((score(e), e) for e in data["excerpts"] if e not in picked), key=lambda x: -x[0])
        picked += [e for s, e in ranked[:MAX_EXCERPTS - len(picked)] if s > 0]
    return picked


def ask(question, ids, history):
    data, by_id = load()
    picked = find(question, ids, by_id, data)
    if not picked:
        return {"answer": "I found no excerpts on that in this index. Try one of the keywords, "
                          "or ask me about an excerpt you have open.", "sources": []}
    blocks = []
    for n, e in enumerate(picked, 1):
        s = data["sessions"][e["s"]]
        asked = f"\n(asked by {e['qb']}: {e['q']})" if e.get("q") else ""
        blocks.append(f"[{n}] {e['by']}, {s['title']} ({s['date']}){asked}\n{e['t']}")
    past = "\n".join(f"{h['role']}: {h['text'][:600]}" for h in history[-4:]) or "(nothing yet)"
    prompt = PROMPT % ("\n\n".join(blocks), past, question[:1000])
    with tempfile.TemporaryDirectory() as empty:
        r = subprocess.run(["opencode", "run", "-m", MODEL, prompt], cwd=empty,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
    out = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout)
    out = out.split("deepseek-v4.1-flash", 1)[-1].strip()      # drop the CLI banner line
    if not out:
        raise RuntimeError("the model gave no answer")
    return {"answer": out, "sources": [e["id"] for e in picked]}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/guide":
            return self.reply(200, {"ok": True})
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/guide":
            return self.reply(404, {"error": "not found"})
        try:
            req = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 20000)))
            self.reply(200, ask(str(req.get("question", "")), list(req.get("ids", [])), list(req.get("history", []))))
        except Exception as e:
            self.reply(500, {"error": str(e)[:200]})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8931
    print(f"http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
