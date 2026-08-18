"""业务逻辑层：命令处理与定时任务共用的纯逻辑。

本模块不依赖 NoneBot matcher，只通过独立函数暴露可复用业务，
供命令层（commands）与定时任务层（scheduler）调用，保持两者职责单一。
"""

import asyncio

from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger

from ..config import config
from ..datasources import d2pt, ti_results
from ..datasources.request_match import (
    request_match_history,
    request_match_info_opendota,
    request_news,
)
from ..generators import core_build, match_builder
from . import store
from .player import Player

_last_news_title = ""

# Steam GetMatchHistory 接口存在速率限制，并发过高易触发 429/503 导致请求失败，
# 因此用信号量限制同批并发拉取比赛历史的数量（并发上限见 config.d2w_history_concurrency）。
_history_semaphore = asyncio.Semaphore(config.d2w_history_concurrency)


# ---------------------------------------------------------------
# 命令业务
# ---------------------------------------------------------------
async def add_player(group_id, nickname: str, steam_id) -> str:
    """订阅玩家；返回提示文案。"""
    if not str(steam_id).isdigit():
        return "steam id 必须是数字"
    if nickname == config.d2w_all_nickname:
        return f"{config.d2w_all_nickname}不是一个合法的昵称"
    reply = store.upsert_player(str(group_id), nickname, int(steam_id))
    store.save()
    return reply


def list_players(group_id) -> str:
    """返回本群玩家列表文案。"""
    players = store.get_all().get(str(group_id), [])
    if not players:
        return "当前群组没有添加任何玩家"
    lines = [f"{p.nickname}（{p.short_steamID}）" for p in players]
    return "本群玩家列表：\n" + "\n".join(lines)


def delete_player(group_id, player_name: str) -> str:
    """删除本群指定玩家；返回提示文案。"""
    reply = store.delete_player(str(group_id), player_name)
    store.save()
    return reply


def toggle_broadcast(group_id, player_name: str, display: bool) -> str:
    """开启/关闭某玩家（或全体）的播报；返回提示文案（空串表示无需回复）。"""
    reply = store.set_display(str(group_id), player_name, display)
    store.save()
    return reply or ""


def toggle_news_subscription(group_id) -> str:
    """切换本群的官方新闻订阅；返回提示文案。"""
    enabled = store.toggle_news_subscription(str(group_id))
    store.save()
    return f"已{'开启' if enabled else '关闭'}官方新闻订阅"


def toggle_ti_subscription(group_id) -> str:
    """切换本群的 TI 赛事订阅；返回提示文案。"""
    enabled = store.toggle_ti_subscription(str(group_id))
    store.save()
    return f"已{'开启' if enabled else '关闭'}TI赛事订阅"


async def d2pt_report(pos: str = "all") -> Message:
    """D2PT 位置数据（文本）。"""
    try:
        # 默认走 1 小时缓存，避免每次触发都重新拉取
        posdata = await d2pt.load_data(force_update=False)
    except Exception:
        logger.exception("d2pt 数据加载失败")
        return Message("d2pt读取数据失败")
    if not posdata:
        return Message("d2pt读取数据失败")

    msg = d2pt.generate_message(posdata, pos)
    if not msg:
        return Message("d2pt读取数据失败")

    return Message(msg)


async def report_image(match_id: str) -> str:
    """生成开黑战报图片，返回本地路径；失败返回空串。"""
    result = await match_builder.generate_report_img(match_id, force=True)
    return result or ""


async def build_image(hero: str, position=None, theme: str = "light") -> str:
    """生成核心出装图片，返回本地路径；失败返回空串。"""
    try:
        result = await core_build.generate_image(hero, position, theme=theme)
        return result or ""
    except Exception:
        logger.exception("出装图生成失败")
        return ""


async def ti_image() -> str:
    """生成 TI 赛事战报图片，返回本地路径；失败返回空串。"""
    try:
        result = await ti_results.generate_league_report_image()
        return result or ""
    except Exception:
        logger.exception("TI 战报生成失败")
        return ""


# ---------------------------------------------------------------
# 群播报
# ---------------------------------------------------------------
async def _broadcast(text: str | None, filter_key: str | None = None) -> None:
    """向群广播一条文本消息。filter_key 为 "subscribe_news"/"subscribe_ti" 时按开关过滤。"""
    if not text:
        return
    bots = get_bots()
    if not bots:
        return
    all_groups = store.get_all_groups()
    msg = Message(f"[DOTA2]{text}")
    for gid, info in all_groups.items():
        if filter_key and not info.get(filter_key, True):
            continue
        for bot in bots.values():
            try:
                await bot.send_group_msg(group_id=int(gid), message=msg)
            except Exception:
                logger.exception(f"广播消息到群 {gid} 失败")


async def _fetch_history(player: Player) -> int | None:
    """获取玩家最近一场比赛 ID；失败时记日志并返回 None。"""
    try:
        async with _history_semaphore:
            return await request_match_history(player, config.d2w_steam_api_key)
    except Exception as e:
        logger.warning(f"获取 {player.nickname} 最近比赛失败: {e}")
        return None


async def _report_match(gid: str, match_id: int, players: list, match_info: dict) -> None:
    """生成并发送一场比赛的战报（图片 + 一句话播报）。"""
    try:
        text = match_builder.generate_message(match_info, players, ezmode=True)
    except Exception:
        logger.exception(f"生成战报文本失败: {match_id}")
        text = None

    pic = None
    try:
        pic = await match_builder.generate_report_img(match_id, force=True)
    except Exception:
        logger.exception(f"生成战报图片失败: {match_id}")

    msg = Message()
    if pic:
        msg += MessageSegment.image(file=pic)
    if text:
        msg += Message(text)
    if not msg:
        return

    bots = get_bots()
    if not bots:
        return
    for bot in bots.values():
        try:
            await bot.send_group_msg(group_id=int(gid), message=msg)
        except Exception:
            logger.exception(f"发送战报到群 {gid} 失败")


# ---------------------------------------------------------------
# 定时任务逻辑
# ---------------------------------------------------------------
async def poll_ti_results() -> None:
    """拉取最新 TI 赛果并广播。"""
    try:
        msg = await ti_results.watch_latest_result(mode="game")
    except Exception:
        logger.exception("TI 结果监听失败")
        return
    await _broadcast(msg, "subscribe_ti")


async def poll_news() -> None:
    """监听 DOTA2 官方新闻，出现新头条时广播。"""
    global _last_news_title
    try:
        news = await request_news()
    except Exception:
        logger.exception("获取 DOTA2 新闻失败")
        return
    events = (news or {}).get("events") or []
    if not events:
        return
    title = events[0].get("event_name")
    news_id = events[0].get("gid")
    if not title:
        return
    if _last_news_title == "":
        # 首次运行仅建立基线，不播报历史新闻
        _last_news_title = title
        return
    if title != _last_news_title:
        _last_news_title = title
        link = f"www.dota2.com/newsentry/{news_id}"
        await _broadcast(f"[news] {title} {link}", "subscribe_news")


async def poll_new_matches() -> None:
    """轮询订阅玩家的新比赛并生成战报播报。"""
    data = store.get_all()
    watched = [
        (gid, player)
        for gid, players in data.items()
        for player in players
        if player.display_recent_match
    ]
    if not watched:
        return

    # 按 steam_id 去重，同一账号只拉取一次比赛历史
    unique_players: dict[int, Player] = {}
    for _, player in watched:
        unique_players.setdefault(player.short_steamID, player)
    unique_list = list(unique_players.values())

    # 阶段一：并发获取去重后玩家的最近比赛 ID
    fetched = await asyncio.gather(
        *(_fetch_history(player) for player in unique_list),
        return_exceptions=True,
    )
    history = dict(zip((p.short_steamID for p in unique_list), fetched))

    new_matches: dict[str, dict[int, list[Player]]] = {}
    match_ids: set[int] = set()
    for gid, player in watched:
        result = history.get(player.short_steamID)
        if isinstance(result, Exception) or not result:
            continue
        if result == player.last_DOTA2_match_ID:
            continue
        new_matches.setdefault(gid, {}).setdefault(result, []).append(player)
        match_ids.add(result)

    if not match_ids:
        return

    # 阶段二：并发获取每场新比赛的详情
    infos = await asyncio.gather(
        *(request_match_info_opendota(mid) for mid in match_ids),
        return_exceptions=True,
    )
    info_map = dict(zip(match_ids, infos))

    changed = False
    for gid, matches in new_matches.items():
        for match_id, players in matches.items():
            match_info = info_map.get(match_id)
            if isinstance(match_info, Exception) or not match_info or "game_mode" not in match_info:
                continue
            for player in players:
                player.last_DOTA2_match_ID = match_id
            changed = True
            # 自定义/活动等模式不播报
            if match_info.get("game_mode") in config.d2w_game_mode:
                continue
            await _report_match(gid, match_id, players, match_info)

    if changed:
        store.save()
