#!/usr/bin/env python3
"""Dota2 适配器:OpenDota 数据 → 统一 match 格式;并给出评级引擎工厂(队伍级)。"""
import json, os, datetime
from core.engine import RatingEngine

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path=None):
    path = path or os.path.join(HERE, "data", "dota_big.json")
    raw = json.load(open(path))
    out = []
    for x in raw:
        r = x.get("radiant") or x.get("r"); d = x.get("dire") or x.get("d")
        rw = x.get("radiant_win"); rw = x.get("rw") if rw is None else rw
        t = x.get("start_time") or x.get("t")
        if not (r and d and rw is not None and t):
            continue
        day = datetime.date.fromtimestamp(t).isoformat()
        out.append({"t": t, "date": day, "year": day[:4], "league": x.get("league", ""),
                    "a": {"team": r, "ents": [r]}, "b": {"team": d, "ents": [d]},
                    "a_won": bool(rw)})
    out.sort(key=lambda x: x["t"])
    return out


def make_engine():
    # 队伍级:w=1;radiant 先手先验 +12;概率收缩 0.7 修过度自信
    return RatingEngine(w=1.0, scale=400, side_adv=12, shrink=0.7, ent=(28, 45, 10))
