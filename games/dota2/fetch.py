#!/usr/bin/env python3
"""
拉取 Dota2 职业比赛数据(OpenDota,免费)。用 explorer SQL 一次拿回近一年,
再存成 dota_big.json。每日 GitHub Action 重跑即可持续累积/刷新。
用法: python3 fetch_dota.py [天数,默认365]
"""
import urllib.request, urllib.parse, json, sys, os, time
HERE=os.path.dirname(os.path.abspath(__file__))
days=int(sys.argv[1]) if len(sys.argv)>1 else 365
sql=("SELECT m.match_id, m.start_time, m.radiant_win, rt.name radiant, dt.name dire, l.name league "
     "FROM matches m "
     "JOIN team_match tmr ON tmr.match_id=m.match_id AND tmr.radiant=true "
     "JOIN team_match tmd ON tmd.match_id=m.match_id AND tmd.radiant=false "
     "JOIN teams rt ON rt.team_id=tmr.team_id JOIN teams dt ON dt.team_id=tmd.team_id "
     "LEFT JOIN leagues l ON l.leagueid=m.leagueid "
     f"WHERE m.radiant_win IS NOT NULL AND m.start_time > (extract(epoch from now())::int - 86400*{days}) "
     "ORDER BY m.start_time DESC LIMIT 60000")
url="https://api.opendota.com/api/explorer?sql="+urllib.parse.quote(sql)
for a in range(4):
    try:
        j=json.loads(urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"ForeGate/1.0"}),timeout=45).read())
        break
    except Exception as e:
        print("retry",str(e)[:60]); time.sleep(3); j=None
rows=(j or {}).get("rows")
if not rows: sys.exit("拉取失败,请重试")
json.dump(rows, open(os.path.join(HERE,"dota_big.json"),"w"))
import datetime
ts=[r["start_time"] for r in rows]
print(f"写出 dota_big.json:{len(rows)} 场 ({datetime.date.fromtimestamp(min(ts))}→{datetime.date.fromtimestamp(max(ts))})")
