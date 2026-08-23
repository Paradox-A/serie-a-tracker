#!/bin/bash
# Requires FOOTBALL_DATA_API_TOKEN env var set (free key from football-data.org)
set -e
curl -s -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/SA/standings" -o standings.json
curl -s -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/SA/matches" -o matches.json
curl -s -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/SA/scorers?limit=50" -o scorers.json

# legaseriea.it's own public stats API (api-sdp.legaseriea.it) — real goals, assists,
# yellow cards, and red cards. No API key needed. Season ID is fixed per season; will
# need updating once the 2026-27 season concludes and a new one begins.
SEASON="serie-a%3A%3AFootball_Season%3A%3Aed7fdc2a3e7b408b942ec177b7b956b5"
BASE="https://api-sdp.legaseriea.it/v1/serie-a/football/seasons/$SEASON/stats/players?category=General&pageNumElement=20&locale=en-GB"
curl -s -H "Referer: https://en.legaseriea.it/" "${BASE}&orderBy=goals-scored&direction=desc" -o sa_goals.json
curl -s -H "Referer: https://en.legaseriea.it/" "${BASE}&orderBy=assists&direction=desc" -o sa_assists.json
curl -s -H "Referer: https://en.legaseriea.it/" "${BASE}&orderBy=yellow-cards&direction=desc" -o sa_yellow.json
curl -s -H "Referer: https://en.legaseriea.it/" "${BASE}&orderBy=red-cards&direction=desc" -o sa_red.json
python3 parse_sa_stats.py
rm -f sa_goals.json sa_assists.json sa_yellow.json sa_red.json

python3 build_site.py
echo "Rebuilt site/index.html"
