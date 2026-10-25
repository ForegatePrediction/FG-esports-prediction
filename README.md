# FG-esports-prediction

An open-source **esports match-prediction framework**. One shared rating engine + series-probability math produces pre-match win probabilities across **11 esports titles**, from a single command-line interface.

一套开源的电竞赛事预测框架:共用「评级引擎 + 系列赛概率数学」,覆盖 11 款电竞项目,统一命令行调用。

> **Disclaimer / 免责声明** — Research & educational framework. All outputs are pre-match statistical estimates and **do not constitute betting or investment advice**. 预测均为盘前统计估计,不构成投注或投资建议。

---

## Core idea

**Rating → single-game win probability `p` → best-of series math → 4 markets.**

Each title reduces to estimating one number — the probability a side wins a single game/map — from which four markets are derived analytically:

- **Match (series) winner** 赛事胜负
- **First game/map winner** 第一局/图胜负
- **Map/game handicap** (e.g. −1.5) 让分
- **Total maps/games** over/under 总局数/图数

The same math serves team games (5v5 MOBA/FPS) and 1v1 (StarCraft): a side is a list of entities (players, or the team itself), so the engine covers `team-only`, `player+team blend`, and `1v1` purely by configuration.

## Supported titles & out-of-sample accuracy

Walk-forward backtest (train on the past, predict forward, no look-ahead). "Series acc." = match-winner hit rate.

| Title | 项目 | Series acc. | Data source |
|---|---|---|---|
| Overwatch | 斗阵特攻 | ~75% | PandaScore |
| League of Legends | 英雄联盟 | ~71% | Oracle's Elixir |
| StarCraft II (1v1) | 星际争霸 II | ~70% | PandaScore |
| Mobile Legends | 决胜巅峰 | ~68% | PandaScore |
| Call of Duty | 使命召唤 | ~68% | PandaScore |
| King of Glory | 王者荣耀 | ~65% | PandaScore |
| Rainbow Six Siege | 彩虹六号 | ~62% | PandaScore |
| Valorant | 无畏契约 | ~62% | PandaScore |
| Dota 2 | Dota 2 | ~62% | PandaScore |
| CS2 | 反恐精英2 | ~62% | PandaScore |
| Brood War (1v1) | 星际:母巢之战 | ~60% | PandaScore |

Accuracy reflects each title's intrinsic variance (MOBAs and 1v1 predict best; some FPS scenes carry more upsets). Probabilities are calibrated — judge over many matches, not a single one. Details in `docs/METHODOLOGY.md`.

## Repository layout

```
core/                 shared across all titles
  engine.py           rating engine (team / player+team blend / 1v1)
  series.py           best-of series -> 4 markets
  backtest.py         walk-forward validation (single-game + series)
  predict.py          zero-training prediction from a ratings snapshot
games/<title>/        one adapter per title
  adapter.py          data -> unified match format + engine config
  config.json         scale / shrink / default best-of / market lines
  fetch.py            pull matches from the free data source
  ratings.json        precomputed rating snapshot (used for prediction)
cli.py                unified entry point
```

## Quickstart

```bash
# Predict (reads the committed ratings snapshot -- no training needed)
python3 cli.py predict lol  "T1" "Gen.G" --bo 5
python3 cli.py predict cs2  "Vitality" "Spirit" --bo 3
python3 cli.py list  sc2  Serral

# Refresh data & re-validate (data is fetched on demand, never committed)
python3 games/<title>/fetch.py       # PandaScore titles need PANDASCORE_TOKEN env
python3 cli.py backtest <title>      # walk-forward accuracy
python3 cli.py snapshot <title>      # rebuild ratings.json
```

Pure Python standard library — no third-party dependencies. Match data is **not** committed (fetched on demand); API tokens live only in environment variables / CI secrets.

## HTTP API

Zero-dependency server that reads the committed rating snapshots — millisecond responses, no data fetch per request.

```bash
python3 server.py            # PORT env, default 8000
```

| Endpoint | 说明 |
|---|---|
| `GET /health` | 健康检查 + 游戏列表 |
| `GET /games` | 所有游戏 + 默认 BO + 准确率 |
| `GET /teams?game=lol&q=T1` | 查队伍/选手(快照内) |
| `GET /predict?game=lol&a=T1&b=Gen.G&bo=5` | 4 玩法 + 逐局胜负 |
| `GET /stats[?game=lol]` | 准确率 |

`/predict` 可选参数:`bo`(默认取该游戏配置)、`hcap`(让分线,默认 1.5)、`total`(总局数线)。CORS 全开,前端可直连。示例返回含 `series_winner / game1_winner / map_handicap / total_maps / correct_score / per_game`。

部署:仓库含 `render.yaml`,在 Render 连接本仓库即可一键部署为 Web 服务(常驻实例秒级响应)。

## Adding a new title

1. `games/<title>/adapter.py` — `load()` maps the source into the unified match format; `make_engine()` returns a configured `RatingEngine`.
2. `config.json` — scale, shrink, side advantage, default best-of, market lines.
3. `fetch.py` — pull from the free data source.
4. `python3 cli.py snapshot <title>` then `backtest <title>` to validate.

No changes to `core/` — that is the point of the framework.

## Data sources

- **League of Legends → Oracle's Elixir** (free; gives per-game rosters, so LoL uses a player+team blended rating — its edge). Kept on OE deliberately: highest accuracy (65% single-map) and widest team coverage.
- **All other 10 titles → PandaScore** (`PANDASCORE_TOKEN` env/secret): consistent, clean (inline team names/scores/BO), broad coverage. Dota 2 and CS2 were migrated from OpenDota / bo3.gg to PandaScore (wider coverage + higher accuracy).

All match data is the property of the respective providers / game publishers and is used here for analysis. Review each provider's terms before production use.

## License

MIT — see `LICENSE`.


## 免费源与每日覆盖证据

LoL 使用 Oracle's Elixir 免费 CSV；Dota 2、CS2、VALORANT、王者荣耀、MLBB、R6、OW、COD、SC2、SCBW 使用 PandaScore 免费 Fixtures 的历史赛程与最终赛果，不调用付费玩家/地图详细统计接口。免费 Fixtures 仍需 `PANDASCORE_TOKEN`；保留此 Token 不代表付费订阅。

每日北京时间 12:00（04:00 UTC）调度。`refresh-status.json` 记录实际抓取状态；`source-coverage.json` 逐游戏、逐联赛保存源数据的最近比赛日期及赛事名称。快照生成时间不代表有新比赛；超过 30 天无源赛果会标记 `stale`，不能按任务绿色判断覆盖正常。
