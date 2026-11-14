# Love/Light Index

An unofficial index of the Confederation channelings published by
[L/L Research](https://www.llresearch.org), from Ra, Q’uo, Hatonn, Latwii, Laitos, Oxal,
L/Leema, Yadda, Yom, Quanta, Monka, Halos, Tovo and Biondha: the whole text, by theme, with
the question that was asked and a link to every original page.

Live at <https://ll.dtun.nl> (with the helper) and <https://meneerkrabs.github.io/love-light-index/>.

## Credits and copyright

All channeled material is **© L/L Research (Louisville, KY)**, all rights reserved, and is
free to read at <https://www.llresearch.org/channeling>. This project is not affiliated
with or endorsed by L/L Research.

The text is reproduced here whole: every session from start to end, in the order it was
given, with the questions as they were asked. Nothing is shortened, reworded or left out,
and every piece carries its source, date, copyright line and a link to the exact turn on
llresearch.org, where the material belongs and is best read.

If L/L Research would like anything changed or removed, please open an issue.

## How it works

- `keywords.json` lists the keywords and the patterns that match them.
- `build.py 1986 1987 …` reads the sessions of those years, one request at a time with a
  pause in between, and writes the site's two data files.
- `site/index.json`: keywords with counts, the session list, sources and years. Small
  (about 23 KB compressed) and loaded first.
- `site/corpus.json`: every piece of text (some 36,000 pieces, 33 million characters, about
  11 MB compressed), loaded once on demand, for keyword pages, sessions, search, permalinks
  and the random piece. It is asked for as `corpus.json?v=<build time>`, so a browser may
  keep it while a new build is always a new URL.
- `site/index.html` is the static page: keywords and subcategories, search, filters on
  source and years, sessions, a random piece, a permanent link per piece, and a page on who
  the sources say they are. The title and description follow the view, so a tab, a bookmark
  and a back button say where you are.
- `static.py` writes the pages a search engine can read: `k/<theme>/` and
  `k/<theme>/<sub>/` (the strongest 100 pieces each), `s/<session>/` (the whole session) and
  `sessions/`, plus `sitemap.xml` and `robots.txt`. Every link in them is relative, so they
  work at the root of ll.dtun.nl and under `/love-light-index/` on GitHub Pages. The
  interactive page stays one page with hash addresses, so nothing needs rewrites on the
  server.

A piece is one speaker turn (questioner turns included), and only a turn longer than 3,000
characters is split, at a paragraph or sentence end, never inside the text. Pieces are filed
under up to three themes, taken from an LLM's reading of the session (`judge.py`) or, where
it has no verdict, from the patterns in `keywords.json`. Each theme carries a strength: the
judge's verdict averaged over the piece's paragraphs, plus how densely the keyword's own
patterns appear, so a long passage that mentions a theme in passing does not outrank a short
one that is entirely about it. A piece that opens with its question ranks above one that
has none, since it makes sense on its own: without a question it counts for 0.6 of its
strength, and a question that is itself about the theme lifts the answer by up to half
again. Theme pages and search open strongest first (search: most matches first), and the
order menu switches to oldest or newest first.

The question a piece answers is carried whole, however long it is; a question over 700
characters is shown folded open on request. Only the piece that opens a turn carries the
question. The rest of that turn says so and links to it, instead of claiming the source
spoke unprompted, and is ranked as one that does not stand on its own.

Search is on whole words, tolerant of endings (`grateful` finds `gratitude` only through
its own word, `love` finds `loving`, `loved`): every word of the query has to be present,
ignoring *the*, *of*, *and* and the like, and the pieces that use the words most often come
first. Typing waits 180 ms before it searches, and the corpus is fetched as soon as the
browser is idle, so neither the first click nor the first keystroke waits for it.

`python3 build.py cache` rebuilds everything from the private local page cache without
touching llresearch.org.

`refresh.sh` runs the whole cycle: reads the current and last year's listings, judges
whatever is new, rebuilds, writes the static pages, publishes to ll.dtun.nl and pushes to
GitHub. It stops before publishing if the rebuild loses pieces. It runs weekly from
`~/Library/LaunchAgents/nl.dtun.quo-index.refresh.plist` (Mondays, 04:07; launchd runs it
when the Mac wakes if it slept through). It does not notice an already-read page changing
upstream: delete that page from `.cache/` and it is read again.

- `judge.py` lets an LLM read candidate paragraphs and say which themes each is about and
  how well it stands alone; `judgments.json` holds the verdicts.
- "The noble helper" is an LLM guide that explains the pieces on screen. It is not Ra or
  any channeled source, claims no truth, cites what it used and tells the reader to read the
  session. `serve.py` runs it locally (through the `opencode` CLI); `server/helper.mjs` is
  the public backend behind https://ll.dtun.nl/api/guide (free OpenAI-compatible APIs, rate
  limited). On GitHub Pages there is no backend, so the helper stays hidden there. It reads
  the site's own corpus (the piece in view and its whole session as context) and refuses
  to reproduce long passages.

```bash
python3 build.py 1986
python3 build.py ra          # the Ra Contact sessions
python3 build.py cache       # everything already cached, no network
python3 -m http.server --directory site
```
