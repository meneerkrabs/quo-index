#!/bin/bash
# Bring the index up to date: read whatever is new on llresearch.org, let the judge file
# it, rebuild the data, write the static pages, publish to ll.dtun.nl and GitHub Pages.
#
# Run by hand, or weekly from launchd (nl.dtun.quo-index.refresh.plist). Safe to run
# twice: session pages already read come from the private cache, only the year listings
# are fetched again, and nothing is published if the rebuild loses pieces.
#
# What it does not do: notice that an already-read page changed upstream. Delete that
# page from .cache/ and it will be read again.
set -uo pipefail
cd "$(dirname "$0")" || exit 1
export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
export LC_ALL=en_US.UTF-8
LOG=refresh.log
log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M')" "$*" >>"$LOG"; }

stat_() { python3 -c "import json;d=json.load(open('site/index.json'));print($1)"; }
pieces_before=$(stat_ 'd["total"]') || { log "stopped: cannot read site/index.json"; exit 1; }
sessions_before=$(stat_ 'len(d["sessions"])')

year=$(date +%Y)
python3 build.py "$year" "$((year - 1))" >>"$LOG" 2>&1
built=$?
pieces_after=$(stat_ 'd["total"]') || pieces_after=0
sessions_after=$(stat_ 'len(d["sessions"])') || sessions_after=0

if [ "$built" -ne 0 ] || [ "$pieces_after" -lt "$pieces_before" ]; then
    log "stopped: build exited $built, pieces $pieces_before -> $pieces_after; nothing published"
    exit 1
fi
if [ "$pieces_after" = "$pieces_before" ] && [ "$sessions_after" = "$sessions_before" ] \
        && [ -f site/sitemap.xml ]; then
    log "nothing new: $pieces_after pieces from $sessions_after sessions"
    exit 0
fi
log "new: $pieces_before -> $pieces_after pieces, $sessions_before -> $sessions_after sessions"

# New paragraphs get a verdict, so they are filed by reading and not by pattern alone.
python3 judge.py >>"$LOG" 2>&1 || log "judge failed; continuing on the keywords"
python3 build.py cache >>"$LOG" 2>&1 || { log "rebuild from cache failed"; exit 1; }
python3 static.py >>"$LOG" 2>&1 || { log "static.py failed"; exit 1; }

rsync -az --delete site/ ubuntu@krokantekrab:ll-stage/ >>"$LOG" 2>&1 \
    || { log "rsync to krokantekrab failed"; exit 1; }
ssh -o BatchMode=yes ubuntu@krokantekrab \
    'sudo rsync -a --delete --chown=root:root --exclude helper.mjs --exclude ll.dtun.nl.conf ~/ll-stage/ /var/www/html/ll/' \
    >>"$LOG" 2>&1 || { log "remote install failed"; exit 1; }

git add -A site judgments.json
if git diff --cached --quiet; then
    log "published; nothing to commit"
    exit 0
fi
git commit -q -m "Refresh: $pieces_after pieces from $sessions_after sessions" \
    -m "Co-Authored-By: Claude Code <noreply@anthropic.com>" >>"$LOG" 2>&1 \
    || { log "commit failed"; exit 1; }
GH_TOKEN=$(gh auth token --user meneerkrabs) git -c credential.helper= \
    -c 'credential.helper=!f() { echo username=meneerkrabs; echo password=$GH_TOKEN; }; f' \
    push -q origin main >>"$LOG" 2>&1 || { log "push failed"; exit 1; }
log "done: $pieces_after pieces from $sessions_after sessions, published and pushed"
