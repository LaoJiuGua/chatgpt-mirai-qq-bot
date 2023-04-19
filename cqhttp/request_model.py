from aiocqhttp import MessageSegment
from typing import Optional, Union, Any
from cqhttp.api import CQApiConfig
from platforms.onebot import bot
from pydantic import BaseModel
from loguru import logger


class SendRequest(BaseModel):

    async def send_request(self, api: str, number_of_retries=4):
        number_of_retries = number_of_retries
        try:
            return await bot.call_action(
                api,
                **self.dict()
            )
        except Exception as e:
            number_of_retries -= 1
            if number_of_retries >= 0:
                logger.info(f"消息发送重试次数-{number_of_retries}")
                return await self.send_request(api, number_of_retries)
            logger.error(f"发送请求失败---{e}")

    async def del_message(self, message_id):
        return await bot.call_action(
            CQApiConfig.message.delete_msg.Api,
            {'message_id': message_id}
        )


class SendPrivateMsgRequest(SendRequest):
    user_id: int
    group_id: Optional[int]
    message: Any
    auto_escape: bool = False


class SendPrivateNodeMsgRequest(SendRequest):
    user_id: int
    messages: Any


class SendGroupMsgRequest(SendRequest):
    group_id: int
    message: Any
    auto_escape: bool = False


class SendGroupNodeMsgRequest(SendRequest):
    group_id: int
    messages: Any


class DeleteMsgRequest(SendRequest):
    message_id: int
