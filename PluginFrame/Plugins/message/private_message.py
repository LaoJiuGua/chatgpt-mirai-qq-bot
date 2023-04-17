import config
from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugins_conf import registration_directive
from loguru import logger
from constants import config
from platforms.onebot import transform_message_chain
from universal import handle_message


@registration_directive(matching=r'^(?![-.#\[\r\n])([\s\S]*)', message_types=("private",))
class PrivateMessagePlugin(BaseComponentPlugin):
    __name__ = 'privateMessage'

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        sender = event.sender
        logger.info(
            f"收到私人消息：{sender.get('nickname')}({sender.get('user_id')})---->{event.message}"
        )
        # 调用GPT-3聊天机器人
        chain = transform_message_chain(event.message)
        await handle_message(
            self.response(event, False),
            f"friend-{event.user_id}",
            event.message,
            chain,
            is_manager=event.user_id == config.onebot.manager_qq,
            nickname=event.sender.get("nickname", "好友")
        )




