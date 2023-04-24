from aiocqhttp import MessageSegment

from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugin_constant import plugin_desc
from PluginFrame.plugins_conf import registration_directive
from constants import config
from middlewares.ratelimit import manager as ratelimit_manager
from utils.text_to_img import to_image


@registration_directive(matching=r'^\.设置 (\w+) (\S+) 额度为 (\d+)条/小时', message_types=("private", "group"))
class SetUpQuotasPlugin(BaseComponentPlugin):
    __name__ = 'SetUpQuotasPlugin'
    desc = "设置每小时GPT额度"
    docs = ".设置 [群组/好友] [群号/QQ号] 额度为 [99]条/小时"
    permissions = ("admin",)

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


@registration_directive(matching=r'#菜单', message_types=("private", "group"))
class MenuPlugin(BaseComponentPlugin):
    __name__ = 'MenuPlugin'

    desc = "功能菜单"
    docs = "#菜单"
    permissions = ("all",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        # 获取机器人对象
        bot = message_parameter.get("bot")
        menu_info = '- ### 功能菜单如下：\n'
        for key, value in plugin_desc.items():
            if not value.get('docs'):
                continue

            if event.message_type in value.get('message_types'):
                permissions = value.get('permissions')
                if not permissions or 'all' in permissions:
                    menu_info += f"- {key} -- {value.get('docs')}\n- - -\n"
                    continue
                if "admin" in permissions:
                    if event.user_id == config.onebot.manager_qq:
                        menu_info += f"- {key} -- {value.get('docs')} **管理员专享**\n- - -\n"
                        continue
                if event.user_id in permissions:
                    menu_info += f"- {key} -- {value.get('docs')}\n- - -\n"
                    continue
        image_info = await to_image(menu_info)
        resp = MessageSegment.image(f"base64://{image_info.base64}")
        await bot.send(event, resp)







## 添加权限



## 关闭插件

