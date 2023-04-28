from hoshino import Service

sv = Service("星铁帮助")

help_txt = '''这是一个HoshinoBot的星穹铁路相关插件，拥有找资源点等功能

指令：

丘丘一下 丘丘语句 ：翻译丘丘语,注意这个翻译只能把丘丘语翻译成中文，不能反向
丘丘词典 丘丘语句 ：查询丘丘语句的单词含义

XXX哪里有：查询XXX的位置图，XXX是资源的名字
星铁资源列表：查询所有的资源名称

星铁黄历
星铁黄历 ： 查看今天的黄历
星铁抽签 ： 抽一签
解签 ： 解答抽签结果
开启\关闭星铁黄历提醒  ： 开启或关闭本群的每日黄历提醒

'''


@sv.on_fullmatch("星铁帮助")
async def help(bot, ev):
    await bot.send(ev, help_txt)
