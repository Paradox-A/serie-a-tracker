import json
from datetime import datetime, timezone
from collections import defaultdict

STANDINGS_PATH = "standings.json"
MATCHES_PATH = "matches.json"
SCORERS_PATH = "scorers.json"
SA_GOALS_PATH = "sa_goals_parsed.json"
SA_ASSISTS_PATH = "sa_assists_parsed.json"
SA_YELLOW_PATH = "sa_yellow_parsed.json"
SA_RED_PATH = "sa_red_parsed.json"
OUT_PATH = "index.html"

SAFETY_THRESHOLD = 40
TOTAL_GAMES = 38

standings_data = json.load(open(STANDINGS_PATH))
table = standings_data["standings"][0]["table"]
season = standings_data["season"]
matchday = season["currentMatchday"]
table = sorted(table, key=lambda t: (t["position"], -t["points"], -t["goalDifference"]))
for i, t in enumerate(table, start=1):
    t["displayPos"] = i

matches_data = json.load(open(MATCHES_PATH))
finished = [m for m in matches_data["matches"] if m["status"] == "FINISHED"]

scorers_data = json.load(open(SCORERS_PATH))
scorers = scorers_data["scorers"]

def load_stat(path):
    return json.load(open(path)) or {}

sa_goals = load_stat(SA_GOALS_PATH)
sa_assists = load_stat(SA_ASSISTS_PATH)
sa_yellow = load_stat(SA_YELLOW_PATH)
sa_red = load_stat(SA_RED_PATH)

def zone_for(pos):
    if pos <= 4:
        return ("cl", "Champions League")
    if pos == 5:
        return ("el", "Europa League")
    if pos == 6:
        return ("ecl", "Conference League")
    if pos >= 18:
        return ("rel", "Relegation")
    return ("", "")

# ---------- League table rows ----------
rows_html = []
for t in table:
    pos = t["displayPos"]
    zone_class, _ = zone_for(pos)
    played = t["playedGames"]
    pts = t["points"]
    gd = t["goalDifference"]
    gd_str = f"+{gd}" if gd > 0 else str(gd)
    form = t.get("form") or "—"
    rows_html.append(f"""
    <tr class="{zone_class}">
      <td class="pos">{pos}</td>
      <td class="team"><img src="{t['team']['crest']}" alt="" class="crest"> {t['team']['shortName']}</td>
      <td>{played}</td><td>{t['won']}</td><td>{t['draw']}</td><td>{t['lost']}</td>
      <td>{t['goalsFor']}</td><td>{t['goalsAgainst']}</td><td>{gd_str}</td>
      <td class="pts">{pts}</td><td class="form">{form}</td>
    </tr>""")

euro_zone = [t for t in table if t["displayPos"] <= 8]
euro_rows = []
fourth = table[3]["points"]
for t in euro_zone:
    pos = t["displayPos"]
    zone_class, zone_label = zone_for(pos)
    label = zone_label if zone_label else "Chasing pack"
    remaining = TOTAL_GAMES - t["playedGames"]
    gap = fourth - t["points"]
    euro_rows.append(f"""
    <tr class="{zone_class}">
      <td class="pos">{pos}</td>
      <td class="team"><img src="{t['team']['crest']}" alt="" class="crest"> {t['team']['shortName']}</td>
      <td>{label}</td><td>{t['points']}</td><td>{remaining}</td>
      <td>{'—' if pos <= 4 else (f'{gap} pt behind 4th' if gap > 0 else 'Level with 4th')}</td>
    </tr>""")

rel_zone = sorted(table, key=lambda t: t["displayPos"])[-6:]
rel_rows = []
for t in rel_zone:
    pos = t["displayPos"]
    remaining = TOTAL_GAMES - t["playedGames"]
    pts = t["points"]
    pts_needed = max(SAFETY_THRESHOLD - pts, 0)
    ppg_needed = (pts_needed / remaining) if remaining > 0 else float('inf')
    if remaining == 0 and pts < SAFETY_THRESHOLD:
        verdict = "Relegated (out of games)"
    elif ppg_needed <= 0:
        verdict = "Already past safety benchmark"
    elif ppg_needed <= 1.0:
        verdict = f"Needs {pts_needed} pts from {remaining} games ({ppg_needed:.2f} pts/game pace)"
    elif ppg_needed <= 1.8:
        verdict = f"Needs {pts_needed} pts from {remaining} games ({ppg_needed:.2f} pts/game — above league-average pace)"
    else:
        verdict = f"Needs {pts_needed} pts from {remaining} games ({ppg_needed:.2f} pts/game — steep, needs a big turnaround)"
    zone_class, _ = zone_for(pos)
    rel_rows.append(f"""
    <tr class="{zone_class}">
      <td class="pos">{pos}</td>
      <td class="team"><img src="{t['team']['crest']}" alt="" class="crest"> {t['team']['shortName']}</td>
      <td>{pts}</td><td>{remaining}</td><td>{verdict}</td>
    </tr>""")

# ---------- Club stats derived from finished matches ----------
club = defaultdict(lambda: {
    "name": None, "crest": None, "gf": 0, "ga": 0, "clean_sheets": 0, "failed_to_score": 0,
    "home_pts": 0, "home_played": 0, "away_pts": 0, "away_played": 0,
    "results": [],
    "biggest_win": None, "heaviest_loss": None,
})

finished_sorted = sorted(finished, key=lambda m: m["utcDate"])
for m in finished_sorted:
    home = m["homeTeam"]; away = m["awayTeam"]
    hs = m["score"]["fullTime"]["home"]; as_ = m["score"]["fullTime"]["away"]
    for side, opp_side, gf, ga, is_home in [(home, away, hs, as_, True), (away, home, as_, hs, False)]:
        c = club[side["id"]]
        c["name"] = side["shortName"]; c["crest"] = side["crest"]
        c["gf"] += gf; c["ga"] += ga
        if ga == 0:
            c["clean_sheets"] += 1
        if gf == 0:
            c["failed_to_score"] += 1
        margin = gf - ga
        result = "W" if margin > 0 else ("D" if margin == 0 else "L")
        c["results"].append(result)
        pts = 3 if result == "W" else (1 if result == "D" else 0)
        if is_home:
            c["home_pts"] += pts; c["home_played"] += 1
        else:
            c["away_pts"] += pts; c["away_played"] += 1
        if result == "W":
            if c["biggest_win"] is None or margin > c["biggest_win"][0]:
                c["biggest_win"] = (margin, f"{gf}-{ga} vs {opp_side['shortName']}")
        if result == "L":
            deficit = ga - gf
            if c["heaviest_loss"] is None or deficit > c["heaviest_loss"][0]:
                c["heaviest_loss"] = (deficit, f"{gf}-{ga} vs {opp_side['shortName']}")

clean_sheet_rows = []
for cid, c in sorted(club.items(), key=lambda kv: (-kv[1]["clean_sheets"], kv[1]["ga"])):
    played = len(c["results"])
    if played == 0:
        continue
    clean_sheet_rows.append(f"""
    <tr>
      <td class="team"><img src="{c['crest']}" alt="" class="crest"> {c['name']}</td>
      <td>{played}</td><td>{c['clean_sheets']}</td>
      <td>{c['ga']/played:.2f}</td><td>{c['failed_to_score']}</td>
    </tr>""")

form_home_away_rows = []
for cid, c in sorted(club.items(), key=lambda kv: -( (kv[1]["home_pts"]+kv[1]["away_pts"]) )):
    played = len(c["results"])
    if played == 0:
        continue
    last5 = "".join(c["results"][-5:])
    home_ppg = (c["home_pts"]/c["home_played"]) if c["home_played"] else 0
    away_ppg = (c["away_pts"]/c["away_played"]) if c["away_played"] else 0
    form_home_away_rows.append(f"""
    <tr>
      <td class="team"><img src="{c['crest']}" alt="" class="crest"> {c['name']}</td>
      <td>{last5 or '—'}</td>
      <td>{c['home_pts']}pts / {c['home_played']}g ({home_ppg:.2f}/g)</td>
      <td>{c['away_pts']}pts / {c['away_played']}g ({away_ppg:.2f}/g)</td>
    </tr>""")

biggest_wins = sorted([ (c["biggest_win"][0], c["name"], c["biggest_win"][1]) for c in club.values() if c["biggest_win"]], reverse=True)[:5]
heaviest_losses = sorted([ (c["heaviest_loss"][0], c["name"], c["heaviest_loss"][1]) for c in club.values() if c["heaviest_loss"]], reverse=True)[:5]
biggest_win_rows = "".join(f"<tr><td>{name}</td><td>{detail}</td></tr>" for _, name, detail in biggest_wins) or "<tr><td colspan='2'>Not enough results yet</td></tr>"
heaviest_loss_rows = "".join(f"<tr><td>{name}</td><td>{detail}</td></tr>" for _, name, detail in heaviest_losses) or "<tr><td colspan='2'>Not enough results yet</td></tr>"

# ---------- Player stats: combined table from football-data scorers ----------
def player_row(s, highlight_field):
    goals = s.get("goals") or 0
    assists_raw = s.get("assists")
    assists = assists_raw or 0
    pens_raw = s.get("penalties")
    pens = pens_raw or 0
    played = s.get("playedMatches") or 0
    involvements = goals + assists
    per_game = (goals/played) if played else 0
    cls = lambda f: "pts" if f == highlight_field else ""
    return f"""
    <tr>
      <td class="team"><img src="{s['team']['crest']}" alt="" class="crest"> {s['player']['name']}</td>
      <td>{s['team']['shortName']}</td>
      <td>{played}</td>
      <td class="{cls('goals')}">{goals}</td>
      <td class="{cls('assists')}">{assists if assists_raw is not None else '—'}</td>
      <td class="{cls('inv')}">{involvements}</td>
      <td>{pens if pens_raw is not None else '—'}</td>
      <td>{per_game:.2f}</td>
    </tr>"""

by_goals = sorted(scorers, key=lambda s: (-(s.get("goals") or 0), -(s.get("assists") or 0)))
goals_rows = "".join(player_row(s, "goals") for s in by_goals)

PLAYER_TABLE_HEAD = """<thead><tr><th class="team">Player</th><th>Club</th><th>Games</th><th>Goals</th><th>Assists</th><th>Goal Inv.</th><th>Pens</th><th>Goals/Game</th></tr></thead>"""

no_scorer_data_note = "" if scorers else """<div class="note">⚠ No scorer data yet — the season hasn't kicked off. This table will populate once matches are played and the site is refreshed.</div>"""

# ---------- Single-stat lists from legaseriea.it's own stats hub (real data) ----------
def sa_stat_table_head(label):
    return f"""<thead><tr><th class="team">Player</th><th>Club</th><th>{label}</th></tr></thead>"""

def sa_stat_rows(stat_dict, limit=15):
    players = sorted(stat_dict.values(), key=lambda p: -(p.get("value") or 0))[:limit]
    if not players:
        return "<tr><td colspan=3>No data yet — season hasn't started</td></tr>"
    rows = []
    for p in players:
        crest = p.get("club", {}).get("logoUrl", "")
        crest_html = f'<img src="{crest}" alt="" class="crest">' if crest else ""
        rows.append(f"""
        <tr>
          <td class="team">{crest_html}{p['name']}</td>
          <td>{p.get('club', {}).get('shortName', '')}</td>
          <td class="pts">{int(p.get('value') or 0)}</td>
        </tr>""")
    return "".join(rows)

GOALS_TABLE_HEAD = sa_stat_table_head("Goals")
ASSISTS_TABLE_HEAD = sa_stat_table_head("Assists")
YELLOW_TABLE_HEAD = sa_stat_table_head("Yellow Cards")
RED_TABLE_HEAD = sa_stat_table_head("Red Cards")

sa_goals_rows = sa_stat_rows(sa_goals)
sa_assists_rows = sa_stat_rows(sa_assists)
sa_yellow_rows = sa_stat_rows(sa_yellow)
sa_red_rows = sa_stat_rows(sa_red)

season_not_started_note = "" if finished else """<div class="note">⚠ The 2026-27 Serie A season is just getting underway — these sections will fill in as matches are played and the site is refreshed.</div>"""

updated = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Serie A 2026-27 Tracker</title>
<style>
  :root {{
    --bg: #f6f1e7; --card: #ffffff; --text: #1a1a1a; --muted: #6b6b6b; --border: #e2ddd0;
    --cl: #d6f5d6; --cl-text: #1a6b1a; --el: #d6e8ff; --el-text: #1a4a8a;
    --ecl: #e0d6ff; --ecl-text: #4a1a8a; --rel: #ffd6d6; --rel-text: #8a1a1a;
    --accent: #0b1c4d; --tab-bg: #eee6d6; --tab-active: #0b1c4d; --tab-active-text: #ffffff;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #16131a; --card: #211d29; --text: #f0ede4; --muted: #a39d8f; --border: #3a3444;
      --cl: #143d14; --cl-text: #8fe08f; --el: #143355; --el-text: #9cc4f5;
      --ecl: #2e1a55; --ecl-text: #c9b3f5;
      --rel: #551a1a; --rel-text: #f5a3a3;
      --accent: #7f9cff; --tab-bg: #2a2534; --tab-active: #7f9cff; --tab-active-text: #16131a;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #16131a; --card: #211d29; --text: #f0ede4; --muted: #a39d8f; --border: #3a3444;
    --cl: #143d14; --cl-text: #8fe08f; --el: #143355; --el-text: #9cc4f5;
    --ecl: #2e1a55; --ecl-text: #c9b3f5;
    --rel: #551a1a; --rel-text: #f5a3a3;
    --accent: #7f9cff; --tab-bg: #2a2534; --tab-active: #7f9cff; --tab-active-text: #16131a;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 24px 16px 60px; }}
  .wrap {{ max-width: 940px; margin: 0 auto; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; color: var(--accent); }}
  .updated {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 18px; }}
  .tabs {{ display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }}
  .tab-btn {{
    background: var(--tab-bg); color: var(--text); border: none; border-radius: 8px;
    padding: 10px 16px; font-size: 0.9rem; font-weight: 600; cursor: pointer;
  }}
  .tab-btn.active {{ background: var(--tab-active); color: var(--tab-active-text); }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 20px; overflow-x: auto; }}
  h2 {{ font-size: 1.1rem; margin-top: 0; }}
  .intro {{ font-size: 0.88rem; color: var(--muted); margin-bottom: 16px; line-height: 1.5; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; white-space: nowrap; }}
  th, td {{ padding: 6px 8px; text-align: center; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; font-size: 0.72rem; text-transform: uppercase; }}
  td.team, th.team {{ text-align: left; }}
  .crest {{ width: 16px; height: 16px; vertical-align: middle; margin-right: 6px; }}
  .pos {{ font-weight: 700; }} .pts {{ font-weight: 700; }}
  tr.cl {{ background: var(--cl); color: var(--cl-text); }}
  tr.el {{ background: var(--el); color: var(--el-text); }}
  tr.ecl {{ background: var(--ecl); color: var(--ecl-text); }}
  tr.rel {{ background: var(--rel); color: var(--rel-text); }}
  .legend {{ display: flex; gap: 14px; flex-wrap: wrap; font-size: 0.78rem; margin-top: 10px; color: var(--muted); }}
  .legend span {{ display: inline-flex; align-items: center; gap: 5px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
  .dot.cl {{ background: var(--cl); }} .dot.el {{ background: var(--el); }}
  .dot.ecl {{ background: var(--ecl); }} .dot.rel {{ background: var(--rel); }}
  .note {{ color: var(--muted); font-size: 0.8rem; margin-top: 8px; }}
  .explainer {{ background: var(--tab-bg); border-radius: 8px; padding: 10px 14px; font-size: 0.82rem; color: var(--text); margin-bottom: 12px; line-height: 1.5; }}
  .explainer b {{ color: var(--accent); }}
  footer {{ text-align: center; color: var(--muted); font-size: 0.75rem; margin-top: 30px; }}
  details.stat-accordion {{ border: 1px solid var(--border); border-radius: 10px; margin-bottom: 12px; overflow: hidden; }}
  details.stat-accordion summary {{
    cursor: pointer; padding: 14px 16px; font-weight: 700; font-size: 0.98rem;
    list-style: none; display: flex; justify-content: space-between; align-items: center;
    background: var(--card);
  }}
  details.stat-accordion summary::-webkit-details-marker {{ display: none; }}
  details.stat-accordion summary::after {{ content: "+"; font-size: 1.2rem; color: var(--muted); }}
  details.stat-accordion[open] summary::after {{ content: "−"; }}
  details.stat-accordion summary .sub {{ font-weight: 400; font-size: 0.78rem; color: var(--muted); margin-top: 2px; display: block; }}
  details.stat-accordion .accordion-body {{ padding: 0 16px 16px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Serie A 2026-27 Tracker</h1>
  <div class="updated">Matchday {matchday} · Last updated {updated}</div>
  {season_not_started_note}

  <div class="tabs">
    <button class="tab-btn active" onclick="showTab('table')">League Table</button>
    <button class="tab-btn" onclick="showTab('club')">Club Stats</button>
    <button class="tab-btn" onclick="showTab('player')">Player Stats</button>
  </div>

  <div id="tab-table" class="tab-panel active">
    <div class="card">
      <h2>League Table</h2>
      <table>
        <thead><tr><th>#</th><th class="team">Team</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GF</th><th>GA</th><th>GD</th><th>Pts</th><th>Form</th></tr></thead>
        <tbody>{"".join(rows_html)}</tbody>
      </table>
      <div class="note"><b>P</b> Played &nbsp;·&nbsp; <b>W</b> Won &nbsp;·&nbsp; <b>D</b> Drawn &nbsp;·&nbsp; <b>L</b> Lost &nbsp;·&nbsp; <b>GF</b> Goals For &nbsp;·&nbsp; <b>GA</b> Goals Against &nbsp;·&nbsp; <b>GD</b> Goal Difference (GF minus GA — the first tiebreaker when teams are level on points) &nbsp;·&nbsp; <b>Pts</b> Points (3 for a win, 1 for a draw, 0 for a loss) &nbsp;·&nbsp; <b>Form</b> results of the last 5 games, oldest to newest</div>
      <div class="legend">
        <span><span class="dot cl"></span>Champions League (1-4)</span>
        <span><span class="dot el"></span>Europa League (5)</span>
        <span><span class="dot ecl"></span>Conference League (6)</span>
        <span><span class="dot rel"></span>Relegation (18-20)</span>
      </div>
      <div class="explainer"><b>New to Serie A?</b> Unlike the Bundesliga, there's no relegation play-off here — the bottom 3 (18th-20th) go straight down to Serie B, no second chance. The Coppa Italia winner can bump the Conference League berth to whichever league position misses out on Europe otherwise, so the exact 6th-place picture can shift late in the season.</div>
    </div>

    <div class="card">
      <h2>European Race</h2>
      <table>
        <thead><tr><th>#</th><th class="team">Team</th><th>Zone</th><th>Pts</th><th>Games Left</th><th>Gap to 4th</th></tr></thead>
        <tbody>{"".join(euro_rows)}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>Relegation Watch</h2>
      <table>
        <thead><tr><th>#</th><th class="team">Team</th><th>Pts</th><th>Games Left</th><th>What it takes to stay up</th></tr></thead>
        <tbody>{"".join(rel_rows)}</tbody>
      </table>
      <div class="note">"Safety" modeled as ~{SAFETY_THRESHOLD} points, a rough historical Serie A survival benchmark over a 38-game season.</div>
    </div>
  </div>

  <div id="tab-club" class="tab-panel">
    <div class="explainer">
      <b>New to Serie A?</b> The table tells you <i>where</i> a team stands, but not <i>how</i> they got there. These stats show the underlying strengths and weaknesses — Serie A has historically been the most defense-minded of Europe's top leagues, so clean-sheet numbers matter more here than almost anywhere else.
    </div>

    <div class="card">
      <h2>Defensive Strength: Clean Sheets</h2>
      <div class="explainer">A <b>clean sheet</b> is a game where a team doesn't concede at all. It's the single clearest sign of defensive solidity — Serie A title winners are almost always among the league's clean-sheet leaders, in a league famous for its defensive tradition (<i>catenaccio</i>).</div>
      <table>
        <thead><tr><th class="team">Team</th><th>Played</th><th>Clean Sheets</th><th>Goals Conceded / Game</th><th>Failed to Score</th></tr></thead>
        <tbody>{"".join(clean_sheet_rows) or "<tr><td colspan=5>No finished matches yet</td></tr>"}</tbody>
      </table>
      <div class="note"><b>Failed to Score</b> counts games where a team didn't score at all — a blunt but telling sign of attacking struggles.</div>
    </div>

    <div class="card">
      <h2>Home Fortress vs. Road Warriors</h2>
      <div class="explainer">Some teams are much stronger at home than away (or the reverse). <b>Points per game (PPG)</b> at home vs. away shows exactly how lopsided that split is. <b>Form</b> is the last 5 results (most recent last) — a better read on momentum than the season-long record.</div>
      <table>
        <thead><tr><th class="team">Team</th><th>Form (last 5)</th><th>Home Record</th><th>Away Record</th></tr></thead>
        <tbody>{"".join(form_home_away_rows) or "<tr><td colspan=4>No finished matches yet</td></tr>"}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>Biggest Wins &amp; Heaviest Losses</h2>
      <div class="explainer">Goal margin matters beyond the 3 points — a big win boosts goal difference (which breaks ties in the table) and can be a statement result against a rival, especially in a Derby d'Italia (Juventus vs. Inter) or Derby della Madonnina (Inter vs. Milan).</div>
      <div style="display:flex; gap:16px; flex-wrap:wrap;">
        <table style="flex:1; min-width:220px;">
          <thead><tr><th class="team">Team</th><th>Biggest Win</th></tr></thead>
          <tbody>{biggest_win_rows}</tbody>
        </table>
        <table style="flex:1; min-width:220px;">
          <thead><tr><th class="team">Team</th><th>Heaviest Loss</th></tr></thead>
          <tbody>{heaviest_loss_rows}</tbody>
        </table>
      </div>
    </div>

    <div class="note" style="margin-top: -8px;">Not shown: possession, shots, passing accuracy, tackles, or expected goals (xG) — these require a paid data source. Everything above is derived directly from final match scores.</div>
  </div>

  <div id="tab-player" class="tab-panel">
    <div class="explainer">
      <b>New to Serie A?</b> The <i>Capocannoniere</i> (top scorer) race is one of Italian football's oldest storylines. Goals alone don't capture everything a player contributes — this table adds context.
    </div>
    {season_not_started_note}
    <div class="card">
      <h2>Top Scorer Race &amp; Goal Involvements</h2>
      <div class="explainer">
        <b>Goals</b>: the headline number, and what decides the Capocannoniere title.<br>
        <b>Assists</b>: the pass that directly leads to a goal — a measure of creativity, not just finishing.<br>
        <b>Goal Involvements</b> (goals + assists): a fuller picture of a player's attacking output.<br>
        <b>Goals/Game</b>: raw totals favor players who've played more games — this rate stat levels the comparison.<br>
        <b>Penalties</b>: shown separately since penalty goals are viewed differently from open-play goals.
      </div>
      <table>{PLAYER_TABLE_HEAD}<tbody>{goals_rows or "<tr><td colspan=8>No scorer data yet</td></tr>"}</tbody></table>
      {no_scorer_data_note}
      <div class="note">Not shown: shots, expected goals (xG), key passes, dribbles, or tackles — this combined table's data source only tracks goals, assists, penalties, and appearances. Deeper stats (like xG) require a paid provider.</div>
    </div>

    <div class="explainer" style="margin-top: 4px;">
      <b>Want just one ranking at a time?</b> The sections below pull real numbers directly from legaseriea.it's own official stats hub — Goals, Assists, Yellow Cards, and Red Cards.
    </div>

    <details class="stat-accordion">
      <summary>Most Goals <span class="sub">The Capocannoniere race — decided by goals alone, nothing else</span></summary>
      <div class="accordion-body">
        <div class="explainer"><b>Goals</b> is the headline number and what the top scorer title is decided by.</div>
        <table>{GOALS_TABLE_HEAD}<tbody>{sa_goals_rows}</tbody></table>
      </div>
    </details>

    <details class="stat-accordion">
      <summary>Most Assists <span class="sub">Who's creating goals for others, not just scoring them</span></summary>
      <div class="accordion-body">
        <div class="explainer"><b>Assists</b> credit the pass (or occasionally the touch) that directly leads to a goal — the clearest single measure of creativity.</div>
        <table>{ASSISTS_TABLE_HEAD}<tbody>{sa_assists_rows}</tbody></table>
      </div>
    </details>

    <details class="stat-accordion">
      <summary>Most Yellow Cards <span class="sub">Discipline — persistent fouling, five in a season triggers an automatic ban</span></summary>
      <div class="accordion-body">
        <div class="explainer">A <b>yellow card</b> is a caution for a foul or unsporting behavior. Two in one match means a red card and an early shower. Accumulate enough yellows across the season and the player serves an automatic one-match ban.</div>
        <table>{YELLOW_TABLE_HEAD}<tbody>{sa_yellow_rows}</tbody></table>
      </div>
    </details>

    <details class="stat-accordion">
      <summary>Most Red Cards <span class="sub">Straight dismissals — an early shower and at least a one-match ban</span></summary>
      <div class="accordion-body">
        <div class="explainer">A <b>red card</b> means immediate ejection from the match, and the team plays the rest of the game a player short. Rare — usually the result of a serious foul, second yellow, or denying an obvious goalscoring opportunity.</div>
        <table>{RED_TABLE_HEAD}<tbody>{sa_red_rows}</tbody></table>
      </div>
    </details>
  </div>

  <footer>Data: football-data.org &amp; legaseriea.it · Rebuilt periodically, not live-updating</footer>
</div>
<script>
function showTab(name) {{
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}}
</script>
</body>
</html>
"""

with open(OUT_PATH, "w") as f:
    f.write(html)
print("wrote", OUT_PATH, len(html), "bytes")
