# Serie A 2026-27 Tracker

A static tracker for Serie A (Italy's top flight), mirroring the Premier League/Bundesliga trackers, with three tabs:
- **League Table**: full standings, color-coded by European qualification zone (Champions League, Europa League, Conference League) and relegation (bottom 3, no play-off), plus a "European Race" view of the top 8 and a "Relegation Watch" view of what each bottom-table team needs to reach safety.
- **Club Stats**: clean sheets, home/away form splits, biggest wins & heaviest losses — all derived from match results.
- **Player Stats**: Top Scorer (Capocannoniere) race, plus expandable lists for Most Goals, Most Assists, Most Yellow Cards, and Most Red Cards.

## Data sources
- [football-data.org](https://www.football-data.org/) free API (Serie A competition code `SA`) — standings, matches, goals/penalties.
- **legaseriea.it's own public stats API** (`api-sdp.legaseriea.it`) — real goals, assists, yellow cards, and red cards, keyed by their own season ID. No API key needed (a `Referer` header is sent for politeness, not because it's required), and each player record includes a direct club crest URL. This is the richest free data source of any league tracked in this project — goals, assists, and both card colors all confirmed working.

**Note on season ID**: the season ID is hardcoded in `fetch_data.sh` (`serie-a::Football_Season::ed7fdc2a3e7b408b942ec177b7b956b5`, URL-encoded). It'll need updating to a new season ID once 2026-27 concludes — check the season dropdown on `en.legaseriea.it/serie-a/statistiche/giocatori` and inspect the page's network requests to find the new ID the same way this one was discovered.

## Regenerating

```bash
export FOOTBALL_DATA_API_TOKEN=your_token_here
./fetch_data.sh
git add index.html
git commit -m "Refresh standings"
git push
```

Not live-updating — rebuild after each matchday (or whenever) to refresh the table.
