#!/bin/bash
# Requires FOOTBALL_DATA_API_TOKEN env var set (free key from football-data.org)
set -e

fetch() {
  # $1 = output file, rest = curl args (URL, headers, etc.)
  local out="$1"; shift
  curl -s "$@" -o "$out"
  if grep -q '"errorCode"' "$out" 2>/dev/null; then
    echo "ERROR: fetch failed for $out — $(cat "$out")" >&2
    exit 1
  fi
  sleep 7
}

fetch standings.json -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/SA/standings"
fetch matches.json -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/SA/matches"
fetch scorers.json -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/SA/scorers?limit=50"

# legaseriea.it's own public stats API (api-sdp.legaseriea.it) — real goals, assists,
# yellow cards, and red cards. No API key needed. Season ID is fixed per season; will
# need updating once the 2026-27 season concludes and a new one begins.
SEASON="serie-a%3A%3AFootball_Season%3A%3Aed7fdc2a3e7b408b942ec177b7b956b5"
BASE="https://api-sdp.legaseriea.it/v1/serie-a/football/seasons/$SEASON/stats/players?category=General&pageNumElement=20&locale=en-GB"
fetch sa_goals.json -H "Referer: https://en.legaseriea.it/" "${BASE}&orderBy=goals-scored&direction=desc"
fetch sa_assists.json -H "Referer: https://en.legaseriea.it/" "${BASE}&orderBy=assists&direction=desc"
fetch sa_yellow.json -H "Referer: https://en.legaseriea.it/" "${BASE}&orderBy=yellow-cards&direction=desc"
fetch sa_red.json -H "Referer: https://en.legaseriea.it/" "${BASE}&orderBy=red-cards&direction=desc"
python3 parse_sa_stats.py
rm -f sa_goals.json sa_assists.json sa_yellow.json sa_red.json

python3 build_site.py
echo "Rebuilt site/index.html"
