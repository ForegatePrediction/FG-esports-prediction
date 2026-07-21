#!/usr/bin/env python3
"""通用轻量预测(全游戏共用)。读 games/<game>/config.json + ratings.json,零训练秒出 4 玩法。"""
import json, os
from .engine import expect
from .series import four_markets, per_game_markets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(game):
    gdir = os.path.join(ROOT, "games", game)
    cfg = json.load(open(os.path.join(gdir, "config.json"), encoding="utf-8"))
    snap = json.load(open(os.path.join(gdir, "ratings.json"), encoding="utf-8"))
    return cfg, snap["teams"]


def _find(teams, name):
    if name in teams:
        return name
    c = [t for t in teams if name.lower() in t.lower() or t.lower() in name.lower()]
    return max(c, key=lambda t: teams[t].get("w", 0) + teams[t].get("l", 0)) if c else None


def predict(game, A, B, bo=None, hcap=1.5, total=None):
    cfg, teams = _load(game)
    a, b = _find(teams, A), _find(teams, B)
    if not a or not b:
        return {"error": f"未找到:{A if not a else B}"}
    bo = bo or cfg.get("default_bo", 3)
    p = 0.5 + (expect(teams[a]["rating"] - teams[b]["rating"], cfg.get("scale", 400)) - 0.5) * cfg.get("shrink", 1.0)
    mk = four_markets(p, bo, hcap_line=hcap, total_line=total)
    mk["per_game"] = per_game_markets(p, bo)
    return {"game": game, "A": a, "B": b, "bo": bo,
            "ratings": {a: teams[a]["rating"], b: teams[b]["rating"]}, "markets": mk}


def list_teams(game, kw):
    _, teams = _load(game)
    kw = kw.lower()
    hits = sorted([(t, v) for t, v in teams.items() if kw in t.lower()], key=lambda x: -x[1]["rating"])
    return hits
