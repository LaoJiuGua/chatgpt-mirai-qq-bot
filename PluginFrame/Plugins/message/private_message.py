import config
from PluginFrame.PluginManager import ModelComponent
from PluginFrame.plugins_conf import registration_directive
from loguru import logger
from constants import config, botManager
from cqhttp.api import CQApiConfig
from cqhttp.cq_code import CqReply


from cqhttp.request_model import SendPrivateMsgRequest
from platforms.onebot import transform_message_chain
from platforms.onebot_bot import response, FriendTrigger
from universal import handle_message
from utils.text_to_img import to_image


@registration_directive(matching=r'^(?![-.#\[\r\n])([\s\S]*)', message_types=("private",))
class PrivateMessagePlugin(ModelComponent):
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
            response(event, True),
            f"friend-{event.group_id}",
            event.message,
            chain,
            is_manager=event.user_id == config.onebot.manager_qq,
            nickname=event.sender.get("nickname", "好友")
        )
        # logger.info(f"回复私人消息：{resp}")
        # if Config.message.text_to_image:
        #     resp = await to_image(resp)
        # resp = CqReply(id=message_id).cq + " " + resp
        # await SendPrivateMsgRequest(user_id=sender.get("user_id"), message=resp).send_request(
        #     CQApiConfig.message.send_private_msg.Api
        # )




