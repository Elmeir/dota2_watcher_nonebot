"""开黑战报：文本生成 + 战报图片调度。"""

import asyncio
import random
import time

from nonebot.log import logger

from ..config import config
from ..dota_dicts import (
    GAME_MODE,
    HEROES_LIST_CHINESE,
    LOBBY,
    LOSE_NEGATIVE,
    LOSE_POSTIVE,
    WIN_NEGATIVE,
    WIN_POSTIVE,
)
from . import match_report


def _mode_label(match_info: dict) -> tuple[str, str]:
    mode = GAME_MODE.get(match_info.get("game_mode"), "未知")
    lobby = LOBBY.get(match_info.get("lobby_type"), "未知")
    return mode, lobby


def _collect_players(match_info: dict, player_list: list) -> list:
    """按 steam_id 匹配并加载每个订阅玩家的对局数据。"""
    collected = []
    for player in player_list:
        for info in match_info.get("players", []):
            if player.short_steamID == info.get("account_id", 0):
                player.load_player_info(info)
                collected.append(player)
                break
        else:
            logger.warning(f"{player.nickname}的数据无法获取，可能已被屏蔽")
    return collected


def generate_message(match_info: dict, player_list: list, ezmode: bool = False) -> str | None:
    """根据比赛数据生成战报文本。

    返回 None 表示该比赛模式不需要播报（如自定义/活动模式）。
    """
    if match_info.get("game_mode") in config.d2w_game_mode:
        return None

    mode, lobby = _mode_label(match_info)
    player_list = _collect_players(match_info, player_list)
    if not player_list:
        return None

    # 队伍信息
    team = player_list[0].stats["dota2_team"]
    teammates = [p for p in match_info.get("players", []) if p.get("team_number") == team]
    team_damage = sum(p.get("hero_damage", 0) for p in teammates)
    team_kills = sum(p.get("kills", 0) for p in teammates)
    team_deaths = sum(p.get("deaths", 0) for p in teammates)

    # 比赛结果
    radiant_win = bool(match_info.get("radiant_win"))
    win = radiant_win if team == 0 else not radiant_win

    # 合并玩家昵称
    if len(player_list) == 1:
        nicknames = player_list[0].nickname
    else:
        nicknames = "、".join(p.nickname for p in player_list)

    positive = check_performance(player_list, win)
    if win and positive:
        text = random.choice(WIN_POSTIVE).format(nicknames)
    elif win:
        text = random.choice(WIN_NEGATIVE).format(nicknames)
    elif positive:
        text = random.choice(LOSE_POSTIVE).format(nicknames)
    else:
        text = random.choice(LOSE_NEGATIVE).format(nicknames)

    if ezmode:
        # 一句话模式：仅返回阴阳怪气标题（详情见战报图片）
        return text

    # 详细模式
    text += "\n"
    text += f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(match_info['start_time']))}\n"
    duration = match_info.get("duration", 0)
    text += f"持续时间: {duration // 60}分{duration % 60}秒\n"
    text += f"游戏模式: [{mode}/{lobby}]\n"

    for player in player_list:
        stats = player.stats
        hero = HEROES_LIST_CHINESE.get(stats["hero"], f"{stats['hero']}不知道什么鬼")
        damage_rate = 0 if team_damage == 0 else 100 * stats["damage"] / team_damage
        participation = (
            0 if team_kills == 0 else 100 * (stats["kill"] + stats["assist"]) / team_kills
        )
        deaths_rate = 0 if team_deaths == 0 else 100 * stats["death"] / team_deaths

        text += f"{player.nickname}使用{hero},\n"
        text += f"KDA: {stats['kda']:.2f}[{stats['kill']}/{stats['death']}/{stats['assist']}],\n"
        text += f"GPM/XPM: {stats['gpm']}/{stats['xpm']},\n"
        text += f"补刀数: {stats['last_hit']},\n"
        text += f"总伤害: {stats['damage']}({damage_rate:.0f}%),\n"
        text += f"参战率: {participation:.0f}%,\n"
        text += f"参葬率: {deaths_rate:.0f}%\n"
    return text


def check_performance(player_list: list, win: bool) -> bool:
    """判断本局战绩是正面还是负面。

    优先使用 openDota 的 benchmark；不可用时退化为 KDA 判断。
    """
    benchmark = player_list[0].stats.get("benchmarks")
    if benchmark:
        total_avg_pct = 0.0
        for player in player_list:
            benchmarks = player.stats.get("benchmarks") or {}
            pcts = [value.get("pct", 0) for value in benchmarks.values()]
            if pcts:
                total_avg_pct += sum(pcts) / len(pcts)
        return total_avg_pct / len(player_list) > config.d2w_benchmark_threshold

    top_kda = max(p.stats["kda"] for p in player_list)
    if (win and top_kda > 8) or (not win and top_kda > 6):
        return True
    if (win and top_kda < 4) or (not win and top_kda < 2):
        return False
    return random.randint(0, 1) == 1


_report_lock = asyncio.Lock()


async def generate_report_img(match_id, force: bool = False):
    """生成战报图片并返回本地路径；失败返回 None/False。

    使用全局锁串行化图片生成，避免多个协程并发操作共享的 aiohttp 会话。
    """
    async with _report_lock:
        try:
            return await match_report.generate_match_image(match_id, force=force)
        finally:
            await match_report.close_session()
