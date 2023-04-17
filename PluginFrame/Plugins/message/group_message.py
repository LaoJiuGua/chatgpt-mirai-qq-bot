from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugins_conf import registration_directive
from loguru import logger

from config import Config
from constants import config
from cqhttp.api import CQApiConfig

from cqhttp.request_model import SendGroupMsgRequest, SendPrivateMsgRequest
from platforms.onebot_bot import transform_message_chain
from universal import handle_message
from utils.text_to_img import to_image


@registration_directive(matching=r'\[CQ:at,qq=(\w+)] ([\s\S]*)', message_types=("group",))
class GroupMessagePlugin(BaseComponentPlugin):
    __name__ = 'groupMessage'

    async def start(self, message_parameter):
        re_obj = message_parameter.get("re_obj")
        event = message_parameter.get("event")
        sender = event.sender
        if re_obj.group(1) != str(event.self_id):
            return

        logger.info(
            f"收到群组({event.group_id})消息：{sender.get('nickname')}({sender.get('user_id')})---->{event.message}"
        )
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



