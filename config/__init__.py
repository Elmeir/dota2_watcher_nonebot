"""插件配置。

所有需要设置 / 调整的项统一集中在本文件：

- `Config`：NoneBot 用户可配置项，可用 `D2W_` 前缀环境变量或 .env 覆盖
  （例如 `D2W_STEAM_API_KEY=...`、`D2W_PROXIES={"http": "...", "https": "..."}`）
- 文件末尾：数据源 URL、目录路径、缓存时长等内部常量

本文件不强制依赖 NoneBot：在独立脚本中直接 `import config` 时，
会退化为使用默认配置，方便脱离框架单独测试生成器脚本。
"""

from pathlib import Path

from pydantic import BaseModel

# ============================================================
# 目录
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"  # 运行时数据（玩家订阅、D2PT 缓存、TI 缓存等）
IMAGES_DIR = BASE_DIR / "images"  # 图片素材
FONTS_DIR = BASE_DIR / "fonts"  # 字体
OUTPUT_DIR = BASE_DIR / "output"  # 生成的战报图片
MATCHES_DIR = BASE_DIR / "matches"  # 比赛 JSON 缓存

# ============================================================
# 上游数据源
# ============================================================
# GitHub 加速前缀（国内访问）
GH_PROXY = "https://gh-proxy.com"

# 上游数据仓库：https://github.com/Elmeir/d2pt_bot
# raw 文件根地址（refs/heads/main 分支）
D2PT_REPO_RAW = "https://raw.githubusercontent.com/Elmeir/d2pt_bot/refs/heads/main"
# 经 gh-proxy 加速后的仓库根 / 数据目录
D2PT_REPO_BASE = f"{GH_PROXY}/{D2PT_REPO_RAW}"
D2PT_DATA_BASE = f"{D2PT_REPO_BASE}/data"
# data/ 目录下的数据 JSON
D2PT_POS_URL = f"{D2PT_DATA_BASE}/d2pt_pos.json"  # D2PT 位置数据（已合并所有位置）
D2PT_CORE_BUILD_URL = f"{D2PT_DATA_BASE}/d2pt_core_build.json"  # 核心出装数据
D2PT_TALENTS_CN_URL = f"{D2PT_DATA_BASE}/talents_cn.json"  # 天赋中文名
# 仓库根 images/abilities/ 技能图标
D2PT_REPO_ICON_BASE = f"{D2PT_REPO_BASE}/images/abilities/"

# 第三方仓库（dotabuff/d2vpkr）技能 ID 列表源
NPC_ABILITY_IDS_URL = f"{GH_PROXY}/https://raw.githubusercontent.com/dotabuff/d2vpkr/master/dota/scripts/npc/npc_ability_ids.txt"

# OpenDota
OPENDOTA_BASE = "https://api.opendota.com"
OPENDOTA_MATCH_URL = f"{OPENDOTA_BASE}/api/matches/{{match_id}}"
OPENDOTA_REQUEST_URL = f"{OPENDOTA_BASE}/api/request/{{match_id}}"
OPENDOTA_LOGS_URL = f"{OPENDOTA_BASE}/logs/{{job_id}}"
OPENDOTA_HEROES_URL = f"{OPENDOTA_BASE}/api/constants/heroes"
OPENDOTA_ITEMS_URL = f"{OPENDOTA_BASE}/api/constants/items"

# Steam Web API
STEAM_API_BASE = "https://api.steampowered.com"
STEAM_MATCH_HISTORY_URL = f"{STEAM_API_BASE}/IDOTA2Match_570/GetMatchHistory/v001/?key={{key}}&account_id={{account_id}}&matches_requested=1"
STEAM_MATCH_DETAILS_URL = (
    f"{STEAM_API_BASE}/IDOTA2Match_570/GetMatchDetails/V001/?key={{key}}&match_id={{match_id}}"
)
STEAM_LIVE_GAMES_URL = f"{STEAM_API_BASE}/IDOTA2Match_570/GetLiveLeagueGames/v1?key={{key}}"
STEAM_NEWS_URL = "https://store.steampowered.com/events/ajaxgetpartnereventspageable/?clan_accountid=0&appid=570&offset=0&count=1&l=schinese"

# Valve DOTA2 官网 / CDN
DOTA2_API_URL = "https://www.dota2.com/webapi/IDOTA2League/GetLeagueData/v001?league_id={league_id}&delay_seconds=0"
DOTA2_HEROES_URL = "https://www.dota2.com/datafeed/herolist?language=schinese"
STEAM_CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react"
HERO_IMAGE_URL = f"{STEAM_CDN}/heroes/{{name}}.png"
ITEM_IMAGE_URL = f"{STEAM_CDN}/items/{{name}}.png"
ABILITY_IMAGE_URL = f"{STEAM_CDN}/abilities/{{name}}.png"
# 战报杂项素材（logo / 段位图标等），同样走 gh-proxy 加速
OTHER_IMAGE_URL = (
    f"{GH_PROXY}/https://raw.githubusercontent.com/SonodaHanami/Steam_watcher/web/images/{{}}.png"
)

# Liquipedia
LIQUIPEDIA_API_URL = "https://liquipedia.net/dota2/api.php?action=parse&page=The_International/2026/Group_Stage&format=json&prop=text&disablelimitreport=1"
LIQUIPEDIA_CDN = "https://liquipedia.net"

# TI 赛事
TI_LEAGUE_ID = 19719
TI_REFERER = "https://www.dota2.com/esports/ti15/schedule"


class Config(BaseModel):
    """NoneBot 用户可配置项（环境变量以 D2W_ 为前缀，如 D2W_TIMEOUT）。"""

    # Steam Web API Key（https://steamcommunity.com/dev/apikey 申请）
    # 用于拉取玩家比赛历史；留空时比赛播报不可用但其余功能正常
    d2w_steam_api_key: str = ""
    # TI 赛事/实时单局使用的 Steam Web API Key（可另申请一个分开用）
    # 留空时回退使用 d2w_steam_api_key
    d2w_ti_steam_api_key: str = ""
    # 代理，如 {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
    d2w_proxies: dict[str, str] = {}
    # 网络请求超时（秒）
    d2w_timeout: int = 20
    # 如何呼叫全体
    d2w_all_nickname: str = "全体"
    # 不播报的游戏模式（见 dota_dicts.GAME_MODE）
    d2w_game_mode: list[int] = [15, 19]
    # 评分标准（0~1），仅 openDota 支持
    d2w_benchmark_threshold: float = 0.5
    # 定时任务轮询间隔（秒）
    d2w_ti_poll_interval: int = 10
    d2w_news_poll_interval: int = 60
    d2w_match_poll_interval: int = 60
    # 数据缓存时长（秒）
    d2w_cache_expire_seconds: int = 3600  # D2PT 位置数据 / 玩家数据缓存
    d2w_core_build_cache_seconds: int = 86400  # 核心出装数据缓存（24 小时）
    # 网络 / 下载 / 分析超时（秒）
    d2w_download_timeout: int = 60
    d2w_match_analysis_timeout: int = 120  # openDota 录像分析等待上限


try:
    # NoneBot 已初始化：读取环境变量 / .env 中的 D2W_ 配置
    from nonebot import get_plugin_config

    config = get_plugin_config(Config)
except Exception:
    # 独立脚本 / 无 NoneBot 环境：使用默认配置
    config = Config()
