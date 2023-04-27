from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugin_constant import get_black_list, del_black_list, set_black_list
from PluginFrame.plugins_conf import registration_directive
from loguru import logger
from constants import config
from platforms.onebot_bot import transform_message_chain
from universal import handle_message


@registration_directive(matching=r'\[CQ:at,qq=(\w+)] ([\s\S]*)', message_types=("group",))
class GroupMessagePlugin(BaseComponentPlugin):
    __name__ = 'groupMessage'
    desc = "群聊GPT回答机器人"
    docs = "@机器人QQ [提问的问题]【无绘画接口】"

    async def start(self, message_parameter):
        re_obj = message_parameter.get("re_obj")
        event = message_parameter.get("event")
        if re_obj.group(1) != str(event.self_id):
            return
        # 调用GPT-3聊天机器人
        chain = transform_message_chain(event.message)
        await handle_message(
            self.response(event, True),
            f"group-{event.group_id}",
            event.message,
            chain,
            is_manager=event.user_id == config.onebot.manager_qq,
            nickname=event.sender.get("nickname", "群友")
        )


@registration_directive(matching=r'#禁用此群', message_types=("group",))
class AddGroupBlacklistPlugin(BaseComponentPlugin):
    __name__ = 'AddGroupBlacklistPlugin'

    desc = "将某群加入黑名单"
    docs = "#禁用此群"
    permissions = ("code",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        # 获取机器人对象
        bot = message_parameter.get("bot")

        if event.group_id in get_black_list("group"):
            return

        set_black_list("group", event.group_id)

        await bot.send(event, "添加成功！")
        return True


@registration_directive(matching=r'#解禁此群', message_types=("group",))
class DelGroupBlacklistPlugin(BaseComponentPlugin):
    __name__ = 'DelGroupBlacklistPlugin'

    desc = "将某群移除黑名单"
    docs = "#解禁此群"
    permissions = ("code",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        # 获取机器人对象
        bot = message_parameter.get("bot")

        if event.group_id in get_black_list("group"):
            del_black_list("group", event.group_id)
            await bot.send(event, "解禁成功！")
        else:
            return



