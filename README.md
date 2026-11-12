# Love/Light Index

An unofficial index of the Ra, Q’uo, Latwii, Hatonn and other Confederation channelings
published by [L/L Research](https://www.llresearch.org): the whole text, by theme, with the
question that was asked and a link to every original page.

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
- `site/index.json` — keywords with counts, the session list, sources and years. Small
  (about 23 KB compressed) and loaded first.
- `site/corpus.json` — every piece of text (some 36,000 pieces, 33 million characters, about
  11 MB compressed), loaded once on demand, for keyword pages, sessions, search, permalinks
  and the random piece.
- `site/index.html` is the static page: keywords and subcategories, search, filters on
  source and years, sessions, a random piece, a permanent link per piece, and a page on who
  the sources say they are.

A piece is one speaker turn — questioner turns included — and only a turn longer than 3,000
characters is split, at a paragraph or sentence end, never inside the text. Pieces are filed
under up to three themes, taken from an LLM's reading of the session (`judge.py`) or, where
it has no verdict, from the patterns in `keywords.json`. `python3 build.py cache` rebuilds
everything from the private local page cache without touching llresearch.org.

- `judge.py` lets an LLM read candidate paragraphs and say which themes each is about and
  how well it stands alone; `judgments.json` holds the verdicts.
- "The noble helper" is an LLM guide that explains the pieces on screen. It is not Ra or
  any channeled source, claims no truth, cites what it used and tells the reader to read the
  session. `serve.py` runs it locally (through the `opencode` CLI); `server/helper.mjs` is
  the public backend behind https://ll.dtun.nl/api/guide (free OpenAI-compatible APIs, rate
  limited). On GitHub Pages there is no backend, so the helper stays hidden there. It reads
  the site's own corpus — the piece in view and its whole session as context — and refuses
  to reproduce long passages.

```bash
python3 build.py 1986
python3 build.py ra          # the Ra Contact sessions
python3 build.py cache       # everything already cached, no network
python3 -m http.server --directory site
```
