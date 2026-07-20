#!/usr/bin/env python3
"""
拉取 CS2 职业比赛数据(bo3.gg 免费公开 API)。系列级 + 地图比分 + 队名。
用法: python3 fetch_cs2.py [回溯到的日期,默认2025-07-01]
每日 GitHub Action 重跑即可增量刷新。
"""
import urllib.request, json, gzip, sys, os, time
HERE=os.path.dirname(os.path.abspath(__file__))
CUT=sys.argv[1] if len(sys.argv)>1 else "2025-07-01"
UA="Mozilla/5.0 (ForeGate; davewell@gphtech.com)"

def getj(url):
    for _ in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Encoding":"gzip"})
            r=urllib.request.urlopen(req,timeout=12); d=r.read()
            if r.headers.get("Content-Encoding")=="gzip": d=gzip.decompress(d)
            return json.loads(d)
        except Exception: time.sleep(0.6)
    return None

def fetch_matches():
    rows=json.load(open(os.path.join(HERE,"cs2_matches.json"))) if os.path.exists(os.path.join(HERE,"cs2_matches.json")) else []
    have=set(x["id"] for x in rows); off=0
    while off < 40000:
        j=getj(f"https://api.bo3.gg/api/v1/matches?filter[status]=finished&filter[discipline_id]=1&sort=-start_date&page[limit]=100&page[offset]={off}")
        if not j or not j.get("results"): break
        for m in j["results"]:
            if m["id"] in have: continue
            have.add(m["id"]); rows.append({"id":m["id"],"t1":m["team1_id"],"t2":m["team2_id"],
                "w":m["winner_team_id"],"s1":m["team1_score"],"s2":m["team2_score"],
                "bo":m["bo_type"],"date":m["start_date"][:10],"tier":m.get("tier")})
        off+=100
        if rows and rows[-1]["date"]<CUT: break
        time.sleep(0.1)
    json.dump(rows,open(os.path.join(HERE,"cs2_matches.json"),"w"))
    return rows

def fetch_names(rows):
    names=json.load(open(os.path.join(HERE,"cs2_teams.json"))) if os.path.exists(os.path.join(HERE,"cs2_teams.json")) else {}
    for off in range(0,2000,100):
        j=getj(f"https://api.bo3.gg/api/v1/teams?sort=rank&page[limit]=100&page[offset]={off}")
        if not j or not j.get("results"): break
        for t in j["results"]:
            if t.get("name"): names[str(t["id"])]=t["name"]
        time.sleep(0.05)
    json.dump(names,open(os.path.join(HERE,"cs2_teams.json"),"w"),ensure_ascii=False)
    return names

if __name__=="__main__":
    r=fetch_matches(); print("matches:",len(r))
    n=fetch_names(r); print("team names:",len(n))
