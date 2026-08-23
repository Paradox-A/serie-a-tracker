import json

def parse(path, stat_key):
    d = json.load(open(path))
    out = {}
    for p in d["players"]:
        stats = {s["statsId"]: s["statsValue"] for s in p["stats"]}
        val = stats.get(stat_key, 0) or 0
        out[p["playerId"]] = {
            "name": p["shortName"],
            "club": {"shortName": p["team"]["shortName"], "logoUrl": "https://media-sdp.legaseriea.it/" + p["team"]["imagery"]["teamLogo"]},
            "value": val,
        }
    return out

for src, dst, key in [
    ("sa_goals.json", "sa_goals_parsed.json", "goals"),
    ("sa_assists.json", "sa_assists_parsed.json", "assists"),
    ("sa_yellow.json", "sa_yellow_parsed.json", "yellow-cards"),
    ("sa_red.json", "sa_red_parsed.json", "red-cards"),
]:
    json.dump(parse(src, key), open(dst, "w"))
    print("wrote", dst)
