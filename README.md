# Confederation sources by keyword

An unofficial keyword index of short excerpts from the Ra, Q’uo, Latwii, Hatonn and other Confederation channelings
published by [L/L Research](https://www.llresearch.org). Every excerpt links to the
exact place in the full session on llresearch.org.

## Credits and copyright

All channeled material quoted here is **© L/L Research (Louisville, KY)**, all rights
reserved, and is free to read in full at <https://www.llresearch.org/channeling>.
This project is not affiliated with or endorsed by L/L Research.

It is built to stay within their [copyright policy](https://www.llresearch.org/copyright),
which allows sharing excerpts with attribution and a link to the source:

- no full transcripts are published or committed; the build keeps a private local cache
  only, so that rebuilding does not load llresearch.org again;
- an excerpt is a single paragraph, shortened to 900 characters and marked `[…]`;
- where there is one, the question it answers is shown above it, shortened to 400 characters;
- at most four paragraphs are quoted from any one session;
- each excerpt shows the source, date, copyright line and a link to the full session.

If L/L Research would like anything changed or removed, please open an issue.

## How it works

- `keywords.json` lists the keywords and the patterns that match them.
- `build.py 1986 1987 …` reads the sessions of those years, one request at a time with
  a pause in between, and writes `site/data.json`.
- `site/index.html` is a static page: excerpts per keyword and subcategory, search, filters
  on source and years, a list of sessions, a random excerpt and a permanent link per excerpt.

Excerpts are chosen by word match. A keyword must occur at least twice in a paragraph
(once for specific terms, three times for very broad ones such as "love"); see `min` in
`keywords.json`. `python3 build.py cache` rebuilds everything from the local cache.

```bash
python3 build.py 1986
python3 build.py ra          # the Ra Contact sessions
python3 -m http.server --directory site
```
