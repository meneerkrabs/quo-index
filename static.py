#!/usr/bin/env python3
"""Write the pages a search engine can read: one for every theme, one for every session
and the list of sessions.

The site itself is a single page that draws its views from two JSON files, which leaves a
crawler with almost nothing to go on. These pages carry the same text as ordinary HTML,
each with its own title, description and canonical address, and each linking into the
interactive site for search, filters and the helper.

Every internal link is relative, so the same pages work at the root of ll.dtun.nl and
under /love-light-index/ on GitHub Pages.

Usage: python3 static.py        (after build.py has written site/corpus.json)
"""
import html
import json
import time
from pathlib import Path

SITE = Path(__file__).parent / "site"
CANON = "https://ll.dtun.nl"
ORIGIN = "https://www.llresearch.org"
TOP = 100          # pieces shown on a theme page; the site itself pages through all of them

CSS = """body{margin:0;background:#f6f2ea;color:#23201b;font:18px/1.65 Georgia,"Iowan Old Style","Times New Roman",serif}
@media (prefers-color-scheme:dark){body{background:#16151a;color:#e9e4d9}a{color:#e0b070}
.count,.q,.src,.who,.kws span{color:#9a9385}article{background:#1e1d24;border-color:#33313a}
footer{border-color:#33313a}}
a{color:#7a4b1e}header,main,footer{max-width:46rem;margin:0 auto;padding:0 1.25rem}
header{padding-top:2.5rem}h1{font-size:2rem;font-weight:normal;margin:0}h1 a{color:inherit;text-decoration:none}
.count{color:#746c5f;font:.9rem system-ui,sans-serif;margin:.25rem 0 1.5rem}
.intro{font-size:.95rem;margin:0 0 1.5rem}
article{background:#fffdf8;border:1px solid #ddd4c4;border-radius:8px;padding:1.1rem 1.4rem;margin:0 0 1.25rem}
article p{margin:0 0 .75rem}.q{color:#746c5f;font-size:.95em;margin:0 0 .4rem}
.q b{font-weight:normal;font-style:italic}.q.none{font:italic .8rem system-ui,sans-serif}
.who{font:.9rem system-ui,sans-serif;color:#746c5f;margin:0 0 .4rem}
.src{font:.82rem/1.5 system-ui,sans-serif;color:#746c5f;margin:0}
nav{font:.95rem system-ui,sans-serif;margin:1rem 0 2rem;display:flex;gap:1.2rem;flex-wrap:wrap}
nav a{text-decoration:none}
.kws{list-style:none;padding:0;columns:3 11rem;column-gap:2rem;font:.9rem system-ui,sans-serif}
.kws li{padding:.15rem 0;border-bottom:1px dotted #ddd4c4;display:flex;gap:.6rem;
justify-content:space-between;break-inside:avoid}
.kws a{text-decoration:none}.kws span{color:#746c5f;font-size:.8rem;flex:none;white-space:nowrap}
h3{font-size:1.1rem;font-weight:normal;margin:1.6rem 0 .4rem}
footer{margin-top:3rem;padding-bottom:3rem;border-top:1px solid #ddd4c4;
font:.85rem/1.6 system-ui,sans-serif;color:#746c5f}"""


def esc(s):
    return html.escape(s, quote=True)


def page(title, desc, canon, body, nav, root):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<style>{CSS}</style>
</head>
<body>
<header><h1><a href="{root}">Love/Light Index</a></h1></header>
<main>
{body}
</main>
<footer>
<p>All channeled material © L/L Research (Louisville, KY), reproduced here in full and
unaltered for study, with a link to the original page on
<a href="{ORIGIN}">www.llresearch.org</a>, where it is free to read. This is an unofficial
index, not affiliated with or endorsed by L/L Research.</p>
<p>{nav}</p>
</footer>
</body>
</html>
"""


def paras(t):
    return "".join(f"<p>{esc(p)}</p>" for p in t.split("\n\n"))


def when(date):
    y, m, d = date.split("-")
    months = ("January February March April May June July August September October "
              "November December").split()
    # two early sessions are listed by month only: /channeling/1972/0300
    return f"{months[int(m) - 1]} {int(d)}, {y}" if d != "00" else f"{months[int(m) - 1]} {y}"


def session_name(s):
    return f"{s['title']} · {s['kind']}" if s.get("kind") else f"{s['title']}, {when(s['date'])}"


def slug(path):
    return path.replace("/channeling/", "").replace("/", "-")


def main():
    index = json.loads((SITE / "index.json").read_text())
    corpus = json.loads((SITE / "corpus.json").read_text())["excerpts"]
    sessions, labels = index["sessions"], {}
    for k in index["keywords"]:
        labels[k["id"]] = k["label"]
        for s in k.get("subs", []):
            labels[f"{k['id']}/{s['id']}"] = s["label"]
    themes = sorted(labels, key=lambda k: labels[k].lower())
    theme_nav = '<a href="{root}">All themes</a><a href="{root}sessions/">Sessions</a>'

    def card(g, root):
        """One piece, with the question it answers, exactly as the site shows it."""
        s = sessions.get(g["s"], {"date": ""})
        if g.get("q"):
            qn = f'<p class="q"><b>{esc(g.get("qb", ""))}:</b> {esc(g["q"])}</p>'
        elif g.get("qs"):
            qn = (f'<p class="q none">Continues an answer: '
                  f'<a href="{root}s/{slug(g["s"])}/#{esc(g["qs"])}">the question is with '
                  f'its first part</a>.</p>')
        elif g.get("r"):
            qn = '<p class="q none">No question recorded: the source spoke unprompted.</p>'
        else:
            qn = ""
        who = esc(g["by"]) + (" " + esc(g["n"]) if g.get("n") else "")
        return (f'<article id="{esc(g["id"])}">{qn}<p class="who"><b>{who}</b></p>{paras(g["t"])}'
                f'<p class="src">©{s.get("date", "")[:4]} by L/L Research (Louisville, KY) · '
                f'<a href="{ORIGIN}{esc(g["s"])}#{esc(g["a"])}">this piece on llresearch.org</a> · '
                f'<a href="{root}s/{slug(g["s"])}/">this session</a></p></article>')

    def write(rel, title, desc, canon, body, nav, root):
        out = SITE / rel / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(title, desc, canon, body, nav, root))

    written = 0
    urls = [(CANON + "/", "1.0", "weekly")]
    for k in index["keywords"]:
        pieces = [g for g in corpus if k["id"] in g["kws"]]
        if not pieces:
            continue
        for key, label, depth in (
                [(k["id"], k["label"], 2)] +
                [(f"{k['id']}/{s['id']}", s["label"], 3) for s in k.get("subs", [])]):
            hits = pieces if key == k["id"] else [g for g in corpus if key in g["kws"]]
            if not hits:
                continue
            root = "../" * depth
            hits = sorted(hits, key=lambda g: -(g.get("w", {}).get(key, 0)))
            by = {}
            for g in hits:
                by[g["by"]] = by.get(g["by"], 0) + 1
            spread = ", ".join(f"{esc(n)} {c}" for n, c in sorted(by.items(), key=lambda x: -x[1]))
            nses = len({g["s"] for g in hits})
            title = f"{label}: {len(hits)} pieces from the L/L Research channelings"
            desc = (f"{len(hits)} pieces on {label.lower()} from {nses} sessions of the "
                    f"L/L Research channelings, whole, with the question that was asked and a "
                    f"link to every original page.")
            body = (f"<h2>{esc(label)}</h2>"
                    f'<p class="count">{len(hits)} pieces from {nses} sessions, strongest first · '
                    f'{spread}</p>'
                    f'<p class="intro">The whole text, in the pieces it was given in, with the '
                    f'question the piece answers. {min(len(hits), TOP)} of them here; the rest, and '
                    f'filters by source and year, are in the '
                    f'<a href="{root}#/k/{key}">interactive index</a>.</p>'
                    f'<nav><a href="{root}">All themes</a><a href="{root}sessions/">Sessions</a>'
                    f'<a href="{root}#/k/{key}">Open in the index</a></nav>')
            body += "".join(card(g, root) for g in hits[:TOP])
            if len(hits) > TOP:
                body += (f'<p class="count">The other {len(hits) - TOP} pieces are in the '
                         f'<a href="{root}#/k/{key}">interactive index</a>.</p>')
            write(f"k/{key}", title, desc, f"{CANON}/k/{key}/", body,
                  theme_nav.format(root=root), root)
            urls.append((f"{CANON}/k/{key}/", "0.8", "weekly"))
            written += 1

    by_session = {}
    for g in corpus:
        by_session.setdefault(g["s"], []).append(g)
    for path, s in sessions.items():
        root = "../../"
        pieces, turns = by_session.get(path, []), []
        for g in pieces:
            # one article per turn: a questioner and the answer to it can share an anchor
            # (Ra Contact numbers them alike), and a piece links back to the article that
            # opens its turn, so the questioner and the source never share one
            if turns and turns[-1]["a"] == g["a"] and turns[-1]["r"] == g.get("r"):
                turns[-1]["parts"].append(g)
            else:
                turns.append({"a": g["a"], "by": g["by"], "r": g.get("r"), "n": g.get("n"),
                              "parts": [g], "q": g.get("q"), "qb": g.get("qb")})
        name = session_name(s)
        title = f"{name}: a session of the L/L Research channelings"
        desc = (f"{when(s['date'])}: the whole session, {s['n']} pieces through "
                f"{', '.join(s['by'])}, complete and in the order it was given.")
        body = (f"<h2>{esc(name)}</h2>"
                f'<p class="count">The whole session, in the order it was given · '
                f'<a href="{ORIGIN}{esc(path)}">the original page on llresearch.org</a> · '
                f'<a href="{root}#/s/{slug(path)}">open in the index</a></p>')
        for t in turns:
            # no question above the answer here: the questioner's own turn is in the text,
            # a line or two above, where it was asked
            body += (f'<article id="{esc(t["parts"][0]["id"])}">'
                     + f'<p class="who"><b>{esc(t["by"])}'
                     + ((" " + esc(t["n"])) if t.get("n") else "") + "</b></p>"
                     + "".join(paras(p["t"]) for p in t["parts"])
                     + f'<p class="src">©{s["date"][:4]} by L/L Research (Louisville, KY) · '
                       f'<a href="{ORIGIN}{esc(path)}#{esc(t["a"])}">this turn on llresearch.org'
                       f"</a></p></article>")
        write(f"s/{slug(path)}", title, desc, f"{CANON}/s/{slug(path)}/", body,
              theme_nav.format(root=root), root)
        urls.append((f"{CANON}/s/{slug(path)}/", "0.6", "yearly"))
        written += 1

    by_year = {}
    for path, s in sessions.items():
        by_year.setdefault(s["date"][:4], []).append(path)
    body = (f'<h2>Sessions</h2><p class="count">{len(sessions)} sessions, all of them '
            f'complete, from {min(by_year)} to {max(by_year)}</p>')
    for y in sorted(by_year, reverse=True):
        body += f"<h3>{y}</h3><ul class=\"kws\">" + "".join(
            f'<li><a href="../s/{slug(p)}/">{esc(session_name(sessions[p]))}</a>'
            f'<span>{esc(", ".join(sessions[p]["by"]))} · {sessions[p]["n"]}</span></li>'
            for p in sorted(by_year[y], key=lambda p: (sessions[p]["date"], p))) + "</ul>"
    write("sessions", "Sessions: every L/L Research channeling, complete",
          f"All {len(sessions)} sessions of the L/L Research channelings, from {min(by_year)} "
          f"to {max(by_year)}, each one whole, by date.",
          CANON + "/sessions/", body, theme_nav.format(root="../"), "../")
    urls.append((CANON + "/sessions/", "0.8", "weekly"))

    stamp = time.strftime("%Y-%m-%d", time.gmtime(index.get("built", time.time())))
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"<url><loc>{u}</loc><lastmod>{stamp}</lastmod>"
                f"<changefreq>{c}</changefreq><priority>{p}</priority></url>\n"
                for u, p, c in urls) + "</urlset>\n")
    (SITE / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: https://ll.dtun.nl/sitemap.xml\n")
    print(f"{written} pages, {len(urls)} addresses in the sitemap", flush=True)


if __name__ == "__main__":
    main()
