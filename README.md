# ForeGate 电竞预测 · 统一框架(foregate-esports-prediction)

一套框架覆盖所有电竞项目。共用一个核心引擎,每个游戏只是一个"适配器"(数据源 + 配置 + 评级快照)。加新游戏 = 加一个 `games/<game>/` 文件夹,不改引擎。

核心思路:**评级 → 单局胜率 p → 系列赛数学 → 4 玩法(赛事胜负 / 第一局 / 局数让分 / 总局数)**。

## 目录

```
core/                 全游戏共用
  engine.py           通用评级引擎(队伍级 / 选手+队伍融合 / 1v1,配置切换)
  series.py           系列赛 4 玩法数学
  backtest.py         走查式回测(单局 + 系列)
  predict.py          零训练轻量预测(读 config + ratings.json)
games/
  lol/                英雄联盟(数据: Oracle's Elixir 免费)
    adapter.py config.json fetch.py ratings.json
  dota2/              Dota2(数据: OpenDota 免费)
    adapter.py config.json fetch.py ratings.json
  cs2/                CS2(数据: bo3.gg 免费)
    adapter.py config.json fetch.py ratings.json
  valorant/           无畏契约(数据: PandaScore 免费档)
    adapter.py config.json fetch.py ratings.json
  kog/                王者荣耀(数据: PandaScore 免费档)
    adapter.py config.json fetch.py ratings.json
cli.py                统一命令入口
```

## 用法(一套命令,所有游戏)

```bash
python3 cli.py backtest lol            # 走查回测(样本外准确率)
python3 cli.py backtest dota2
python3 cli.py snapshot dota2          # 由数据重建评级快照 ratings.json
python3 cli.py predict lol  "T1" "Gen.G" --bo 5
python3 cli.py predict dota2 "Team Falcons" "Team Liquid" --bo 3
python3 cli.py list dota2 Spirit       # 模糊查队名
```

给运营 / AI agent:直接读 `games/<game>/ratings.json` 的 `rating`,套 `p = shrink*(logistic((rA-rB)/scale)-0.5)+0.5`,再由 `core/series.py` 展开 4 玩法即可。

## 各游戏样本外准确率(走查式、纯样本外)

| 游戏 | 单局命中率 | 系列赛命中率 | Brier | 说明 |
|---|---|---|---|---|
| 英雄联盟 LoL | 65.4% | 70.7% | 0.216 | 选手+队伍融合评级 |
| Dota2 | 57.6% | 57.7% | 0.239 | 队伍级;高方差游戏,天花板偏低 |
| CS2 | 57.0% | ~58% | 0.245 | 队伍级(按地图展开);数据 3.5 个月,历史越多越稳 |
| 无畏契约 Valorant | 60.6% | ~61.8% | 0.235 | 队伍级(按地图展开);一年数据,PandaScore |
| 王者荣耀 King of Glory | 59.3% | ~65% | 0.239 | 队伍级(按小局展开);约1.5年数据,PandaScore |

> 诚实说明:命中率是游戏本身特性决定的——LoL 分层清晰(~65%),Dota2 爆冷多(~57%)。两者概率都已校准(Brier/LogLoss 优于瞎猜)。对外按真实数字设预期,按多场累计判断,不虚高。

## 加一个新游戏怎么做

1. 建 `games/<game>/`,写 `adapter.py`:`load()` 把该游戏数据转成统一 match 格式,`make_engine()` 返回配好参数的 `RatingEngine`。
2. 写 `config.json`(scale / shrink / side_adv / default_bo / 盘口线 / 回测方式)。
3. 写 `fetch.py`(免费数据源采集)。
4. `python3 cli.py snapshot <game>` 生成评级快照;`backtest` 验证准确率。

数据文件不入库(`games/*/data/` 已在 .gitignore),用各游戏 `fetch.py` 现拉;每日 GitHub Action 可自动刷新。

> 预测均为盘前统计估计,不构成投注建议。
