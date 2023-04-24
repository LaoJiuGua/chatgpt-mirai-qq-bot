from PluginFrame.Plugins import BaseComponentPlugin
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



