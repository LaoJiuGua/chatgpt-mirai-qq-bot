import base64
import io
import os
import pathlib
import re
import uuid
from io import BytesIO
import requests
from loguru import logger
from PIL import Image
from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugin_constant import choose_data, set_choose_data, get_choose_data, del_choose_data, get_manager_qq, \
    path
from PluginFrame.plugins_conf import registration_directive
from cqhttp.api import CQApiConfig
from cqhttp.request_model import MessageSegment, SendPrivateMsgRequest, SendGroupMsgRequest, GetMessage


@registration_directive(matching=r'^#(美女视频|菠萝拌饭|帅哥视频|西施美女|蹲下变装|体操服系|你的欲梦)', message_types=("private", "group"))
class DouYinBellePlugin(BaseComponentPlugin):
    __name__ = 'DouYinBellePlugin'
    desc = "抖音MM短视频"
    docs = '#美女视频|菠萝拌饭|帅哥视频|西施美女|蹲下变装|体操服系|你的欲梦'
    permissions = ("all",)
    plu_name = '视频插件'

    async def start(self, message_parameter):

        message_info = message_parameter.get("event")
        sender = message_info.sender
        re_obj = message_parameter.get("re_obj")
        title = re_obj.group(1)
        # message = MessageSegment.video(self.get_girl_url(title))
        message = MessageSegment.video(f"https://api.caonm.net/api/cdmn/m?lx={title}&key=d73IGg5Nn4hXl0a8CzHeUrGUgV",
                                       cache=False)
        if message_info.get("message_type") == "group":
            await SendGroupMsgRequest(group_id=message_info.get("group_id"), message=message).send_request(
                CQApiConfig.message.send_group_msg.Api
            )
        elif message_info.get("message_type") == "private":
            await SendPrivateMsgRequest(user_id=sender.get("user_id"), message=message).send_request(
                CQApiConfig.message.send_private_msg.Api
            )



    @staticmethod
    def get_girl_url(title):
        resp = requests.get(f"https://api.caonm.net/api/cdmn/m?lx={title}&key=d73IGg5Nn4hXl0a8CzHeUrGUgV")
        video_path = f"{uuid.uuid4()}.mp4"
        with open(video_path.replace("-", ""), "wb") as f:
            f.write(resp.content)
        # try:
        #     url = resp.history[1].url
        # except:
        #     url = "http://xin-hao.top/sqlWork/randomDouyin"
        # logger.info("取到的url为：{}".format(url))
        return video_path.replace("-", "")


@registration_directive(matching=r'^#视频搜索(\d+|) (.*)-(\d+)', message_types=("private", "group"))
class VideoPlugin(BaseComponentPlugin):
    __name__ = 'VideoPlugin'
    desc = "视频搜索(支持动漫、电影)"
    docs = '#视频搜索[解析渠道1~∞][视频名称]-[页数]'
    permissions = ("admin",)
    plu_name = '视频插件'

    async def start(self, message_parameter):

        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        re_obj = message_parameter.get("re_obj")
        num, msg, page = re_obj.groups()
        if not num.strip():
            num = 1
        if not page.strip():
            page = 1
        wait_info = await bot.send(event, MessageSegment.reply(event.get("message_id")).__add__(
            MessageSegment.text('请稍后...')
        ))

        status, message_info = self.get_video_url(msg, num, page)

        await self.del_wait(wait_info.get("message_id"))
        if not status:
            await bot.send(event, message_info)
            await self.del_wait(wait_info.get("message_id"))
            return

        if event.get("message_type") == "group":
            await self.send(self.send_group_node_msg, group_id=event.get("group_id"))(
                messages=message_info
            )

        elif event.get("message_type") == "private":
            await self.send(self.send_private_node_msg, user_id=event.get("user_id"))(
                messages=message_info
            )

    @staticmethod
    def get_video_url(msg, num, page):
        count = 10
        if int(num) <= 0:
            num = 1
        if int(page) <= 0:
            page = 1

        _list = []
        try:
            resp = requests.get(f"https://api.pearktrue.cn/api/search/video.php?msg={msg}&num={num}", timeout=60)
            video_data = resp.json()

            if video_data.get("code") not in (200, '200'):
                return False, video_data.get("msg")

            video_data_list = video_data.get("data", []) or []
            try:
                video_data_list_new = video_data_list[(int(page)-1)*count: count*int(page)]
            except Exception as e:
                video_data_list_new = []

            if not video_data_list_new:
                return False, "暂无查询结果"

            message_title = MessageSegment.node_custom(
                nickname="北.", user_id=1113855149,
                content=f"""视频名称：{video_data.get('videoname')}\n类型：{video_data.get('videostate')}\n页数:{page}"""
            )
            _list.append(message_title)

            for data in video_data_list_new:
                link = data.get('link')
                try:
                    resp_url = requests.get(f"https://api.pearktrue.cn/api/short/dwz.php?url={link}", timeout=5)
                    resp_url_data = resp_url.json()
                    if resp_url_data.get("code") in ("200", 200):
                        link = resp_url_data.get("short_url")
                except:
                    ...

                message = MessageSegment.node_custom(
                    nickname="北.", user_id=1113855149,
                    content=f"""{MessageSegment(type_="reply", data={"text": f"{data.get('name')}", "qq": 1113855149})}{link}"""
                )
                _list.append(message)

            return True, _list
        except Exception as e:
            print(e)
            return False, "请求出现问题！！"
