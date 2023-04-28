
from loguru import logger
from hoshino import Service
from .query_resource_points import get_resource_map_mes, get_resource_list_mes, init_point_list_and_map

sv = Service("星铁资源查询")


@sv.on_rex(r"(\w+)(?:在哪|在哪里|哪有|哪里有)")
@sv.on_rex(r"(?:哪有|哪里有)(\w+)")
async def inquire_resource_points(bot, ev):
    resource_name = ev['match'].group(1)
    if resource_name == "":
        return

    await bot.send(ev, await get_resource_map_mes(resource_name), at_sender=True)


@sv.on_fullmatch('星铁资源列表')
async def inquire_resource_list(bot, ev):
    # 长条消息经常发送失败，所以只能这样了
    mes_list = []
    txt_list = get_resource_list_mes().split("\n")
    for txt in txt_list:
        data = {
            "type": "node",
            "data": {
                "name": "色图机器人",
                "uin": "2854196310",
                "content": txt
            }
        }
        mes_list.append(data)
    # await bot.send(ev, get_resource_list_mes(), at_sender=True)
    await bot.send_group_forward_msg(group_id=ev['group_id'], messages=mes_list)


@sv.on_fullmatch('刷新星铁资源列表')
async def refresh_resource_list(bot, ev):
    await init_point_list_and_map()
    await bot.send(ev, '刷新成功', at_sender=True)


@sv.on_fullmatch('更新星铁地图')
async def up_map_icon(bot, ev):
    await init_point_list_and_map()
    await bot.send(ev, '更新成功', at_sender=True)
