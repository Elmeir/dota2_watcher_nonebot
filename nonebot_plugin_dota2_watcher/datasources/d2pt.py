"""D2PT 位置数据：抓取、缓存、解析与格式化。"""

import json
import time
from pathlib import Path
from typing import Any

from nonebot.log import logger

from ..config import D2PT_POS_URL, DATA_DIR, config
from ..dota_dicts import HEROES_LIST_CHINESE
from ..utils import DOTA2HTTPError, get_http_client

CACHE_EXPIRE_SECONDS = config.d2w_cache_expire_seconds  # 缓存时长（秒）
POS_RAW_FILE = DATA_DIR / "d2pt_pos.json"  # 远程合并的全位置原始数据缓存
POS_DATA_FILE = DATA_DIR / "d2pt_data.json"  # 解析后的全位置数据
_URL = D2PT_POS_URL


def _load_json(path: Path, default=None):
    """读取本地 JSON 缓存；解析失败或文件损坏时返回 default。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


async def fetch_d2pt_cheatsheet() -> dict:
    """从远程拉取合并后的全位置原始数据，并写入本地缓存。"""
    url = _URL
    client = await get_http_client()
    try:
        response = await client.get(url)
    except Exception:
        raise DOTA2HTTPError(f"{CACHE_EXPIRE_SECONDS}秒内无法连接到网站，建议检查网络")
    if response.status_code >= 400:
        raise DOTA2HTTPError(f"D2PT 数据获取失败：{response.status_code}")
    d2pt_data = response.json()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    POS_RAW_FILE.write_text(json.dumps(d2pt_data, ensure_ascii=False, indent=4), encoding="utf-8")
    return d2pt_data


async def get_data_with_cache() -> dict:
    """读取全位置原始数据，缓存过期或缺失时自动拉取；
    远程拉取失败时回退使用本地缓存（即使已过期）。"""
    cached = _load_json(POS_RAW_FILE) if POS_RAW_FILE.exists() else None
    if cached is not None:
        age = time.time() - POS_RAW_FILE.stat().st_mtime
        if age < CACHE_EXPIRE_SECONDS:
            return cached
    try:
        return await fetch_d2pt_cheatsheet()
    except DOTA2HTTPError:
        # 远程拉取失败：回退读取本地缓存（即使已过期）
        if cached is not None:
            logger.warning("D2PT 远程数据拉取失败，回退使用本地缓存")
            return cached
        raise


def parse_data_pos(pos: int, data: list) -> list:
    """将原始数据解析为按综合评分排序的英雄列表。"""
    if not data:
        return []
    matches_filter = max(h.get("matches", 0) for h in data) / 10

    result = []
    for h in data:
        hero_id = h["hero_id"]
        hero_name_cn = HEROES_LIST_CHINESE.get(hero_id, str(hero_id))
        matches = h.get("matches", 0)
        wins = h.get("wins", 0)
        lane = h.get("detailed_stats", {}).get("lane_avg_adv_pct", 0)
        if lane < 0.01 and lane > -0.01:
            lane_score = lane
        elif pos < 5:
            lane_score = (abs(lane * 100) ** 0.5) * (-1 if lane < 0 else 1) / 100
        else:
            lane_score = lane
        win_rate = wins / matches if matches else 0
        score = win_rate + lane_score
        if matches >= matches_filter and win_rate >= 0.5:
            result.append(
                {
                    "id": hero_id,
                    "name": hero_name_cn,
                    "WR": f"{win_rate:.1%}",
                    "lane": f"{lane:.1%}",
                    "lane_score": f"{lane_score:.1%}",
                    "score": f"{score:.1%}",
                }
            )
    result.sort(key=lambda item: item["score"], reverse=True)
    return result


async def parse_data(force_update: bool = False) -> dict:
    """抓取/刷新全部 1-5 号位数据，并缓存到 d2pt_data.json。"""
    raw = await get_data_with_cache()
    pos_all: dict[str, Any] = {}
    for pos in (1, 2, 3, 4, 5):
        raw_pos = (raw or {}).get(f"pos{pos}", [])
        if raw_pos:
            pos_all[str(pos)] = parse_data_pos(pos, raw_pos)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    POS_DATA_FILE.write_text(json.dumps(pos_all, ensure_ascii=False, indent=4), encoding="utf-8")
    return pos_all


async def load_data(force_update: bool = False) -> dict | None:
    """读取合并后的全位置数据；d2pt_data.json 缓存过期或缺失时重新解析。
    远程拉取失败时回退使用本地缓存（即使已过期）。"""
    cached = _load_json(POS_DATA_FILE) if POS_DATA_FILE.exists() else None
    if cached is not None:
        age = time.time() - POS_DATA_FILE.stat().st_mtime
        if age < CACHE_EXPIRE_SECONDS and not force_update:
            return cached
    try:
        return await parse_data(force_update)
    except DOTA2HTTPError:
        # 远程拉取失败：回退读取本地缓存（即使已过期）
        if cached is not None:
            logger.warning("D2PT 远程数据拉取失败，回退使用本地缓存")
            return cached
        raise


def generate_message(data: dict, pos: str = "all") -> str:
    """格式化输出指定位置（或全部）的英雄数据。"""
    full_space = chr(12288)
    lines = []

    def _header(title: str) -> str:
        return f"{title:{full_space}<6}{'  胜率':<10}{'线优'}"

    def _row(item: dict) -> str:
        if "-" in item["lane"]:
            return f"{item['name']:{full_space}<6}{item['WR']:<7}{item['lane']}"
        return f"{item['name']:{full_space}<6}{item['WR']:<8}{item['lane']}"

    if pos == "all":
        for p in (1, 2, 3, 4, 5):
            lines.append(_header(f"{p}号位"))
            lines.extend(_row(item) for item in data.get(str(p), [])[:5])
            lines.append("")
    elif str(pos) in ("1", "2", "3", "4", "5"):
        lines.append(_header(f"{pos}号位"))
        lines.extend(_row(item) for item in data.get(str(pos), [])[:15])

    return "\n".join(lines).rstrip("\n")
