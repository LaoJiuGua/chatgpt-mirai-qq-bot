import re
import time
import requests
from loguru import logger

from PluginFrame.PluginManager import ModelComponent
from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugins_conf import registration_directive
from config import Config
from cqhttp import SendMsgModel
from cqhttp.api import CQApiConfig
from cqhttp.request_model import SendRequest, MessageSegment, SendPrivateMsgRequest, SendGroupMsgRequest, \
    DeleteMsgRequest
from platforms.onebot_bot import transform_from_message_chain

from utils.text_to_img import to_image


@registration_directive(matching=r'^#(美女|放松心情|轻松一刻)', message_types=("private", "group"), permissions=("admin",))
class DouYinBellePlugin(BaseComponentPlugin):
    __name__ = 'DouYinBellePlugin'

    async def start(self, message_parameter):

        message_info = message_parameter.get("event")
        sender = message_info.sender
        # 调用GPT-3聊天机器人

        message = MessageSegment.video(self.get_girl_url())
        if message_info.get("message_type") == "group":
            logger.info(
                f"收到群组({message_info.get('group_id')})消息：{sender.get('nickname')}({sender.get('user_id')})---->{message_info.get('message')}"
            )
            await SendGroupMsgRequest(group_id=message_info.get("group_id"), message=message).send_request(
                CQApiConfig.message.send_group_msg.Api
            )
        elif message_info.get("message_type") == "private":
            logger.info(
                f"收到私人消息：{sender.get('nickname')}({sender.get('user_id')})---->{message_info.get('message')}"
            )
            await SendPrivateMsgRequest(user_id=sender.get("user_id"), message=message).send_request(
                CQApiConfig.message.send_private_msg.Api
            )

    def get_girl_url(self):

        resp = requests.get("http://xin-hao.top/sqlWork/randomDouyin")
        try:
            url = resp.history[1].url
        except:
            url = "http://xin-hao.top/sqlWork/randomDouyin"
        logger.info("取到的url为：{}".format(url))
        return url


@registration_directive(matching=r'^#(ping|Ping) (.*)', message_types=("private", "group"), permissions=("admin",))
class PingHostPlugin(BaseComponentPlugin):
    __name__ = 'PingHostPlugin'

    async def start(self, message_parameter):
        message_info = message_parameter.get("event")
        sender = message_info.sender
        re_obj = message_parameter.get("re_obj")
        host = re_obj.group(2)
        if message_info.get("message_type") == "group":
            logger.info(
                f"收到群组({message_info.get('group_id')})消息：{sender.get('nickname')}({sender.get('user_id')})---->{message_info.get('message')}"
            )

            wait_info = await self.send_wait(self.send_group_msg, group_id=message_info.get("group_id"))(
                message_info.get("message_id"), "请稍后..."
            )
            status, data = self.get_girl_url(host)
            await self.del_wait(wait_info.get("message_id"))
            data = f"{MessageSegment.reply(message_info.get('message_id'))} {data}"
            await self.send_group_msg(message_info.get("group_id"), str(data))

        elif message_info.get("message_type") == "private":
            logger.info(
                f"收到私人消息：{sender.get('nickname')}({sender.get('user_id')})---->{message_info.get('message')}"
            )

            wait_info = await self.send_wait(self.send_private_msg, user_id=message_info.get("user_id"))(
                message_info.get("message_id"), "请稍后..."
            )
            status, data = self.get_girl_url(host)

            await self.del_wait(wait_info.get("message_id"))
            await self.send_private_msg(sender.get("user_id"), data)
        return ''

    @staticmethod
    def get_girl_url(url):
        resp = requests.get(f"https://v.api.aa1.cn/api/api-ping/ping.php?url={url}")
        try:
            resp = resp.json()
            data = f"""
            Ping {url} 的结果为：
             域名：{resp.get("host")}
             IP：{resp.get("ip")}
             最小延迟：{resp.get("ping_time_min")}
             最大延迟：{resp.get("ping_time_max")}
             服务器运营部：{resp.get("location")}
             服务器归属地：{resp.get("node")}
            """
            status = 0
        except Exception as e:
            print(e)
            data = resp.text
            status = 1
        return status, data


@registration_directive(matching=r'^#舔狗', message_types=("private", "group"), permissions=("all",))
class AnimeWallpapersPlugin(BaseComponentPlugin):
    __name__ = 'AnimeWallpapersPlugin'

    async def start(self, message_parameter):

        message_info = message_parameter.get("event")
        sender = message_info.sender
        # 调用GPT-3聊天机器人

        if message_info.get("message_type") == "group":
            logger.info(
                f"收到群组({message_info.get('group_id')})消息：{sender.get('nickname')}({sender.get('user_id')})---->{message_info.get('message')}"
            )
            wait_info = await self.send_wait(self.send_group_msg, group_id=message_info.get("group_id"))(
                message_info.get("message_id"), "请稍后..."
            )
            await self.del_wait(wait_info.get("message_id"))

            data = MessageSegment.reply(message_info.get('message_id')).text(self.get_girl_url())

            await self.send(self.send_group_msg, user_id=message_info.get("user_id"))(
                message=str(data)
            )

        elif message_info.get("message_type") == "private":

            logger.info(
                f"收到私人消息：{sender.get('nickname')}({sender.get('user_id')})---->{message_info.get('message')}"
            )
            wait_info = await self.send_wait(self.send_private_msg, user_id=message_info.get("user_id"))(
                message_info.get("message_id"), "请稍后..."
            )
            await self.del_wait(wait_info.get("message_id"))

            data = MessageSegment.reply(message_info.get('message_id')).__add__(
                MessageSegment.text(self.get_girl_url()))

            await self.send(self.send_private_msg, user_id=message_info.get("user_id"))(
                message=str(data)
            )

    def get_girl_url(self):
        try:
            resp = requests.get("https://v.api.aa1.cn/api/tiangou/")
            text = re.findall(r"<p>(.*?)</p>", resp.text)
        except:
            text = ["接口似乎出现问题了！！"]
        return text[0]


@registration_directive(matching=r'^#今日热点', message_types=("private", "group"), permissions=("admin",))
class TodayHotSpotPlugin(BaseComponentPlugin):
    __name__ = 'TodayHotSpotPlugin'

    async def start(self, message_parameter):
        message_info = message_parameter.get("event")

        if message_info.get("message_type") == "group":

            wait_info = await self.send_wait(self.send_group_msg, group_id=message_info.get("group_id"))(
                message_info.get("message_id"), "请稍后..."
            )
            await self.del_wait(wait_info.get("message_id"))

            await self.send(self.send_group_node_msg, group_id=message_info.get("group_id"))(
                messages=self.get_girl_url()
            )

        elif message_info.get("message_type") == "private":

            wait_info = await self.send_wait(self.send_private_msg, user_id=message_info.get("user_id"))(
                message_info.get("message_id"), "请稍后..."
            )
            await self.del_wait(wait_info.get("message_id"))

            await self.send(self.send_private_node_msg, user_id=message_info.get("user_id"))(
                messages=self.get_girl_url()
            )

    def get_girl_url(self):
        try:
            resp = requests.get("https://v.api.aa1.cn/api/topbaidu/")
            _dict_list = []
            for _ in resp.json().get("newslist"):
                if not _.get('digest'):
                    continue
                message = MessageSegment.node_custom(
                    nickname="北.", user_id=1113855149,
                    content=f"""{
                    MessageSegment(type_="reply", data={"text": _.get('title'), "qq": 1113855149})
                    } {
                    MessageSegment.text(_.get('digest'))
                    }
                    """
                )
                _dict_list.append(message)
        except:
            _dict_list = [MessageSegment.node_custom(nickname="北.", user_id=1113855149, content=f"接口似乎出现问题了！！")]
        return _dict_list
