#!/usr/bin/env python3
"""
ForeGate 电竞预测 · 统一 API(零依赖,Python 标准库)。
只读各游戏已提交的评级快照(games/<g>/ratings.json)——秒级响应、无需拉数据。
本地: python3 server.py  (PORT 环境变量,默认 8000)

路由:
  GET /health
  GET /games                                  所有游戏 + 准确率
  GET /teams?game=lol&q=T1                     查队伍/选手(快照内)
  GET /predict?game=lol&a=T1&b=Gen.G&bo=5      预测 4 玩法 + 逐局
  GET /stats[?game=lol]                        准确率
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import predict as P

ROOT = os.path.dirname(os.path.abspath(__file__))
GAMES_DIR = os.path.join(ROOT, "games")

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Max-Age": "86400",
}


def list_games():
    out = {}
    for g in sorted(os.listdir(GAMES_DIR)):
        cfg = os.path.join(GAMES_DIR, g, "config.json")
        if os.path.isfile(cfg):
            c = json.load(open(cfg, encoding="utf-8"))
            out[g] = {"name": c.get("name", g), "default_bo": c.get("default_bo", 3),
                      "accuracy": c.get("accuracy", ""), "source": c.get("source", "")}
    return out


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body):
        payload = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in CORS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        path = u.path.rstrip("/") or "/"
        try:
            if path in ("/", "/health"):
                return self._send(200, {"status": "ok", "service": "foregate-esports-prediction",
                                        "games": list(list_games().keys())})
            if path == "/games":
                return self._send(200, list_games())
            if path == "/stats":
                gl = list_games()
                if q.get("game"):
                    g = q["game"]
                    return self._send(200 if g in gl else 404,
                                      gl.get(g, {"error": f"unknown game {g}"}))
                return self._send(200, {g: {"name": v["name"], "accuracy": v["accuracy"]}
                                        for g, v in gl.items()})
            if path == "/teams":
                g = q.get("game"); kw = q.get("q", "")
                if not g:
                    return self._send(400, {"error": "缺少 game 参数"})
                try:
                    hits = P.list_teams(g, kw)
                except FileNotFoundError:
                    return self._send(404, {"error": f"unknown game {g}"})
                return self._send(200, {"game": g, "count": len(hits),
                                        "teams": [{"name": t, "rating": v["rating"],
                                                   "w": v.get("w"), "l": v.get("l")} for t, v in hits[:60]]})
            if path == "/predict":
                g = q.get("game"); a = q.get("a"); b = q.get("b")
                if not (g and a and b):
                    return self._send(400, {"error": "需要 game / a / b 参数"})
                bo = int(q["bo"]) if q.get("bo") else None
                hcap = float(q.get("hcap", 1.5))
                total = float(q["total"]) if q.get("total") else None
                lang = "en" if q.get("lang") == "en" else "zh"
                try:
                    r = P.predict(g, a, b, bo=bo, hcap=hcap, total=total, lang=lang)
                except FileNotFoundError:
                    return self._send(404, {"error": f"unknown game {g}"})
                return self._send(200 if "error" not in r else 400, r)
            return self._send(404, {"error": "not found",
                                    "endpoints": ["/health", "/games", "/teams", "/predict", "/stats"]})
        except Exception as e:
            return self._send(500, {"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"ForeGate esports API on :{port}")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
