"""命令处理器：玩家订阅 / 播报开关 / d2pt / 战报 / 出装 / ti。

命令层只负责解析输入、调用 services 中的业务函数并返回结果，
业务逻辑统一放在 services.py 中。
"""

from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.matcher import Matcher

from . import services

# ---------------------------------------------------------------
# 命令注册
# ---------------------------------------------------------------
add_player_cmd = on_command("添加刀塔玩家", priority=10, block=True)
list_players_cmd = on_command("查看刀塔玩家", priority=10, block=True)
delete_player_cmd = on_command(
    "删除刀塔玩家", priority=10, block=True, permission=GROUP_ADMIN | GROUP_OWNER
)
close_broadcast_cmd = on_regex(r"关闭(\S+)的群播报", priority=10, block=True)
open_broadcast_cmd = on_regex(r"开启(\S+)的群播报", priority=10, block=True)
d2pt_cmd = on_command("d2pt", aliases={"D2PT"}, priority=10, block=True)
report_cmd = on_command("战报", priority=10, block=True)
build_cmd = on_command("出装", priority=10, block=True)
ti_cmd = on_command("ti", aliases={"TI"}, priority=10, block=True)
subscribe_cmd = on_command(
    "订阅", priority=10, block=True, permission=GROUP_ADMIN | GROUP_OWNER
)


def _args(event: GroupMessageEvent) -> list[str]:
    """取命令名之后以空格分隔的参数列表。"""
    return event.get_plaintext().strip().split()[1:]


# ---------------------------------------------------------------
# 添加玩家
# ---------------------------------------------------------------
@add_player_cmd.handle()
async def handle_add_player(event: GroupMessageEvent):
    parts = event.get_plaintext().strip().split()
    if len(parts) != 3:
        await add_player_cmd.finish(
            "请输入：/添加刀塔玩家 [玩家昵称] [steam的id]\n如：/添加刀塔玩家 萧瑟先辈 898754153"
        )
    reply = await services.add_player(event.group_id, parts[1], parts[2])
    await add_player_cmd.finish(reply)


# ---------------------------------------------------------------
# 查看玩家
# ---------------------------------------------------------------
@list_players_cmd.handle()
async def handle_list_players(event: GroupMessageEvent):
    await list_players_cmd.finish(services.list_players(event.group_id))


# ---------------------------------------------------------------
# 删除玩家（管理员以上）
# ---------------------------------------------------------------
@delete_player_cmd.handle()
async def handle_delete_player(event: GroupMessageEvent):
    args = _args(event)
    if len(args) != 1:
        await delete_player_cmd.finish("请输入：/删除刀塔玩家 [玩家昵称]")
    await delete_player_cmd.finish(services.delete_player(event.group_id, args[0]))


# ---------------------------------------------------------------
# 播报开关
# ---------------------------------------------------------------
@close_broadcast_cmd.handle()
async def handle_close_broadcast(matcher: Matcher, event: GroupMessageEvent):
    name = matcher.state["_matched_groups"][0]
    if reply := services.toggle_broadcast(event.group_id, name, display=False):
        await close_broadcast_cmd.finish(reply)


@open_broadcast_cmd.handle()
async def handle_open_broadcast(matcher: Matcher, event: GroupMessageEvent):
    name = matcher.state["_matched_groups"][0]
    if reply := services.toggle_broadcast(event.group_id, name, display=True):
        await open_broadcast_cmd.finish(reply)


# ---------------------------------------------------------------
# /d2pt
# ---------------------------------------------------------------
@d2pt_cmd.handle()
async def handle_d2pt(event: GroupMessageEvent):
    args = _args(event)
    if len(args) > 1:
        await d2pt_cmd.finish("请输入：/d2pt 或 /d2pt [位置(数字)]")
    pos = args[0] if args else "all"
    if pos != "all" and pos not in "12345":
        await d2pt_cmd.finish("请输入：/d2pt 或 /d2pt [位置(数字)]")
    await d2pt_cmd.finish(await services.d2pt_report(pos))


# ---------------------------------------------------------------
# /战报
# ---------------------------------------------------------------
@report_cmd.handle()
async def handle_report(event: GroupMessageEvent):
    args = _args(event)
    if len(args) != 1 or not args[0].isdigit():
        await report_cmd.finish("请输入：/战报 [比赛编号]")
    if path := await services.report_image(args[0]):
        await report_cmd.finish(MessageSegment.image(file=path))
    await report_cmd.finish("战报生成失败")


# ---------------------------------------------------------------
# /出装
# ---------------------------------------------------------------
@build_cmd.handle()
async def handle_build(event: GroupMessageEvent):
    args = _args(event)
    if not args:
        await build_cmd.finish("请输入：/出装 [英雄名] [位置(数字)] [dark|light]")
    hero, position, theme = args[0], None, "light"
    if len(args) >= 2 and args[1] in "12345":
        position = args[1]
        if len(args) >= 3:
            theme = "dark" if args[2] == "dark" else "light"
    elif len(args) >= 2:
        await build_cmd.finish("位置参数无效，请输入 1-5")
    if path := await services.build_image(hero, position, theme):
        await build_cmd.finish(MessageSegment.image(file=path))
    await build_cmd.finish("没有找到该数据")


# ---------------------------------------------------------------
# /ti
# ---------------------------------------------------------------
@ti_cmd.handle()
async def handle_ti():
    if path := await services.ti_image():
        await ti_cmd.finish(MessageSegment.image(file=path))
    await ti_cmd.finish("查询失败，官网炸了")


# ---------------------------------------------------------------
# 订阅开关（管理员以上，切换：开启<->关闭）
# ---------------------------------------------------------------
@subscribe_cmd.handle()
async def handle_subscribe(event: GroupMessageEvent):
    args = _args(event)
    if len(args) != 1:
        await subscribe_cmd.finish("请输入：/订阅 新闻 或 /订阅 ti")
    target = args[0].strip().lower()
    if target in ("新闻", "news"):
        await subscribe_cmd.finish(services.toggle_news_subscription(event.group_id))
    if target in ("ti", "赛事"):
        await subscribe_cmd.finish(services.toggle_ti_subscription(event.group_id))
    await subscribe_cmd.finish("请输入：/订阅 新闻 或 /订阅 ti")
