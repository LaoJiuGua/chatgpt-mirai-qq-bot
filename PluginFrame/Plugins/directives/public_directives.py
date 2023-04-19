from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugins_conf import registration_directive
from middlewares.ratelimit import manager as ratelimit_manager


@registration_directive(matching=r'^\.设置 (\w+) (\S+) 额度为 (\d+)条/小时', message_types=("private", "group"),
                        permissions=("admin",))
class SetUpQuotasPlugin(BaseComponentPlugin):
    __name__ = 'SetUpQuotasPlugin'

    async def start(self, message_parameter):

        event = message_parameter.get("event")
        # 获取正则对象
        re_obj = message_parameter.get("re_obj")
        # 获取机器人对象
        bot = message_parameter.get("bot")
        msg_type, msg_id, rate = re_obj.groups()

        if msg_type not in ["群组", "好友"]:
            return await bot.send(event, "类型异常，仅支持设定【群组】或【好友】的额度")
        if msg_id != '默认' and not msg_id.isdecimal():
            return await bot.send(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
        ratelimit_manager.update(msg_type, msg_id, int(rate))
        return await bot.send(event, "额度更新成功！")
