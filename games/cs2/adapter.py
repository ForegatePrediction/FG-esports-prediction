#!/usr/bin/env python3
"""CS2 适配器:bo3.gg 系列数据 → 按地图展开成统一 match 格式;队伍级评级引擎。"""
import json, os, datetime
from core.engine import RatingEngine

HERE = os.path.dirname(os.path.abspath(__file__))


def load(data_dir=None):
    data_dir = data_dir or os.path.join(HERE, "data")
    raw = json.load(open(os.path.join(data_dir, "cs2_matches.json")))
    names = {}
    tp = os.path.join(data_dir, "cs2_teams.json")
    if os.path.exists(tp):
        names = json.load(open(tp))
    nm = lambda i: names.get(str(i)) or f"team#{i}"
    today = datetime.date.today().isoformat()
    out = []
    for x in raw:
        if not (isinstance(x["s1"], int) and isinstance(x["s2"], int) and x["w"]):
            continue
        if x["s1"] == x["s2"] or x["bo"] not in (1, 3, 5) or x["date"] > today:
            continue
        A, B = nm(x["t1"]), nm(x["t2"])
        a_won_series = x["w"] == x["t1"]
        d = x["date"]
        # 按地图比分展开成逐图结果(队伍级评级用),同一系列同日同两队 → series_backtest 会重新聚合
        k = 0
        for _ in range(x["s1"]):
            out.append(_row(d, x["id"], k, A, B, True)); k += 1
        for _ in range(x["s2"]):
            out.append(_row(d, x["id"], k, A, B, False)); k += 1
    out.sort(key=lambda z: z["t"])
    return out


def _row(date, mid, k, A, B, a_won):
    return {"t": f"{date}#{mid:012d}#{k}", "date": date, "year": date[:4], "league": "",
            "a": {"team": A, "ents": [A]}, "b": {"team": B, "ents": [B]}, "a_won": a_won}


def make_engine():
    # 队伍级(w=1);列表顺序不是真实先手,故 side_adv=0
    return RatingEngine(w=1.0, scale=400, side_adv=0, shrink=1.0, ent=(28, 48, 8))
