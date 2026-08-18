# DOTA2 Watcher

基于 [NoneBot2](https://nonebot.dev/) 的 DOTA2 观察者插件，为 QQ 群提供开黑战报、玩家比赛播报、TI 赛事监听、DOTA2 新闻推送与 D2PT 出装等能力。

## 功能特性

- **开黑战报**：输入比赛编号，生成包含对局详情与 MVP 评分的战报图片（基于 OpenDota）。
- **玩家比赛播报**：添加 / 查看 / 删除订阅玩家，自动轮询其最新比赛并生成战报推送。
- **新闻推送**：DOTA2 官方新闻出现新头条时自动向群广播。
- **TI 赛事**：定时拉取 TI 赛果并推送，支持 `/ti` 查看实时战报图片。
- **D2PT 出装**：查询 D2PT 各位置胜率 / 线优数据，以及指定英雄的核心出装图片（支持明暗主题）。
- **播报开关**：按群 / 按玩家开启或关闭播报（昵称填「全体」可一次控制全部）。

## 安装

本插件基于 NoneBot2 + OneBot v11 适配器，请先部署好 NoneBot2 运行环境（Python >= 3.10）。

```bash
# 1. 安装 NoneBot2 与 OneBot v11 适配器
pip install nonebot2 nonebot-adapter-onebot

# 2. 安装本插件依赖
pip install nonebot-plugin-apscheduler httpx aiohttp Pillow fonttools playwright

# 3. 将本插件目录放入 NoneBot2 项目的 plugins/ 目录
```

> 本插件使用 Playwright 渲染部分页面，请额外安装浏览器内核：
>
> ```bash
> python -m playwright install chromium
> ```

在 NoneBot2 的 `pyproject.toml`（或机器人的 `bot.py`）中加载插件：

```python
# bot.py
import nonebot
from nonebot.adapters.onebot.v11 import Adapter

nonebot.init()
driver = nonebot.get_driver()
driver.register_adapter(Adapter)
nonebot.load_plugin("dota2_watcher_nonebot")  # 或使用 plugins 目录自动加载
nonebot.run()
```

## 配置

所有配置项均以 `D2W_` 前缀通过环境变量或 `.env` 文件设置，或直接修改 [`config/__init__.py`](config/__init__.py)。

| 环境变量                           | 说明                                                                           | 默认值        |
| ------------------------------ | ---------------------------------------------------------------------------- | ---------- |
| `D2W_STEAM_API_KEY`            | Steam Web API Key（用于拉取玩家比赛历史），[申请地址](https://steamcommunity.com/dev/apikey)  | 空          |
| `D2W_TI_STEAM_API_KEY`         | TI 赛事 / 实时单局使用的独立 API Key，留空时复用上面的 Key                                       | 空          |
| `D2W_PROXIES`                  | 网络代理，如 `{"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}` | `{}`       |
| `D2W_TIMEOUT`                  | 网络请求超时（秒）                                                                    | `20`       |
| `D2W_ALL_NICKNAME`             | “全体”播报的昵称关键字                                                                 | `全体`       |
| `D2W_GAME_MODE`                | 不播报的游戏模式列表                                                                   | `[15, 19]` |
| `D2W_BENCHMARK_THRESHOLD`      | 评分标准（0\~1，仅 OpenDota 支持）                                                     | `0.5`      |
| `D2W_TI_POLL_INTERVAL`         | TI 赛果轮询间隔（秒）                                                                 | `10`       |
| `D2W_NEWS_POLL_INTERVAL`       | 新闻轮询间隔（秒）                                                                    | `60`       |
| `D2W_MATCH_POLL_INTERVAL`      | 玩家比赛轮询间隔（秒）                                                                  | `60`       |
| `D2W_CACHE_EXPIRE_SECONDS`     | D2PT / 玩家数据缓存时长（秒）                                                           | `3600`     |
| `D2W_CORE_BUILD_CACHE_SECONDS` | 核心出装数据缓存时长（秒）                                                                | `86400`    |
| `D2W_DOWNLOAD_TIMEOUT`         | 下载超时（秒）                                                                      | `60`       |
| `D2W_MATCH_ANALYSIS_TIMEOUT`   | OpenDota 录像分析等待上限（秒）                                                         | `120`      |

示例 `.env`：

```dotenv
D2W_STEAM_API_KEY=你的Steam_Web_API_Key
D2W_PROXIES={"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
D2W_TIMEOUT=20
```

## 使用方法

在群内发送以下命令（`/` 前缀命令需确保机器人已启用命令前缀）：

| 命令                                | 说明                       | 权限  |
| --------------------------------- | ------------------------ | --- |
| `/添加刀塔玩家 [昵称] [steam的id]`         | 订阅玩家，新比赛自动播报             | 任意  |
| `/查看刀塔玩家`                         | 查看本群已订阅玩家列表              | 任意  |
| `/删除刀塔玩家 [昵称]`                    | 删除本群指定玩家                 | 管理员 |
| `开启[昵称]的群播报`                      | 开启某玩家的播报（昵称填“全体”可一次控制全部） | 任意  |
| `关闭[昵称]的群播报`                      | 关闭某玩家的播报                 | 任意  |
| `/d2pt [位置1-5]`                   | 查看 D2PT 胜率 / 线优数据        | 任意  |
| `/战报 [比赛编号]`                      | 生成开黑战报图片                 | 任意  |
| `/出装 [英雄名] [位置1-5] [dark\|light]` | 生成核心出装图片                 | 任意  |
| `/ti`                             | 查看 TI 赛事战报图片             | 任意  |
| `/订阅 新闻`                          | 开启 / 关闭官方新闻订阅            | 管理员 |
| `/订阅 ti`                          | 开启 / 关闭 TI 赛事订阅          | 管理员 |

> 示例：`/添加刀塔玩家 萧瑟先辈 898754153`、`/出装 敌法师 1 dark`、`/战报 1000000000`。

## 目录结构

```
├── commands.py        # 命令处理器
├── services.py        # 业务逻辑层
├── scheduler.py       # 定时任务（TI / 新闻 / 玩家比赛轮询）
├── config/
│   ├── __init__.py       # 插件配置
├── match_builder.py   # 开黑战报生成
├── core_build.py      # 核心出装图生成
├── d2pt.py            # D2PT 数据
├── ti_results.py      # TI 赛果
├── fonts/             # 字体资源
└── ...
```

## 致谢

- [NoneBot2](https://nonebot.dev/)
- [OpenDota](https://www.opendota.com/) / Steam Web API 提供的比赛数据
- [d2pt\_bot](https://github.com/Elmeir/d2pt_bot) 提供的 D2PT 出装与位置数据
- [Steam\_watcher](https://github.com/SonodaHanami/Steam_watcher) 提供的战报素材

