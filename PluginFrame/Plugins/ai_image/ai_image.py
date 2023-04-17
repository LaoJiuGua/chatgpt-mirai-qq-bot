import random
import base64
import json
import re
import time
import websockets
import requests
from loguru import logger
from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugins_conf import registration_directive
from config import Config
from constants import config
from cqhttp.api import CQApiConfig
from cqhttp.request_model import SendRequest, MessageSegment

token = None


@registration_directive(matching=r'^#画(.*?)', message_types=("private", 'group'))
class AiImagePlugin(BaseComponentPlugin):
    __name__ = 'AiImagePlugin'

    async def start(self, message_parameter):
        # 调用GPT-3聊天机器人
        re_obj = message_parameter.get("re_obj")
        event = message_parameter.get("event")
        sender = event.sender
        message_id =event.message_id
        # 调用GPT-3聊天机器人

        if event.get("message_type") == "group":
            logger.info(
                f"收到Ai绘画消息：{re_obj.group(1)}"
            )

            wait_info = await self.send_wait(self.send_group_msg, group_id=event.get("group_id"))(
                event.get("message_id"), "请稍后..."
            )
            avatar_str = self.ai_painting(re_obj.group(1))
            await self.del_wait(wait_info.get("message_id"))

            if avatar_str == -6:
                await self.send_group_msg(event.get("group_id"), "绘画失败，包含非法字符！")
                return

            avatar_str = base64.b64decode(avatar_str)
            image_cq = MessageSegment.reply(id_=message_id).__add__(
                MessageSegment.image(
                    file="base64://" + base64.b64encode(avatar_str).decode()
                )
            )
            await self.send_group_msg(event.get("group_id"), str(image_cq))

        elif event.get("message_type") == "private":
            logger.info(
                f"收到Ai绘画消息：{re_obj.group(1)}"
            )
            wait_info = await self.send_wait(self.send_private_msg, user_id=event.user_id)(
                event.get("message_id"), "请稍后..."
            )
            avatar_str = self.ai_painting(re_obj.group(1))
            await self.del_wait(wait_info.get("message_id"))

            if avatar_str == -6:
                await self.send_private_msg(event.get("user_id"), "绘画失败，包含非法字符！")
                return

            avatar_str = base64.b64decode(avatar_str)
            image_cq = MessageSegment.reply(id_=message_id).__add__(
                MessageSegment.image(
                    file="base64://" + base64.b64encode(avatar_str).decode()
                )
            )
            await self.send_private_msg(sender.get("user_id"), str(image_cq))

    def get_token(self):
        global token
        if not token:
            res = requests.get(
                "https://flagopen.baai.ac.cn/flagStudio/auth/getToken",
                headers={"Accept": "application/json"}, params={"apikey": config.baai.apiKey}
            )
            logger.info("获取绘画Token")
            if res.status_code == 200:
                logger.info("获取绘画Token成功---{}".format(res.json().get("data").get("token")))
                token = res.json().get("data").get("token")
                return token
        logger.info("使用已有Token---{}".format(token))
        return token

    def ai_painting(self, prompt):

        token_key = self.get_token()
        url = "https://flagopen.baai.ac.cn/flagStudio/v1/text2img"

        style = ["国画", "写实主义", "虚幻引擎", "黑白插画", "版绘", "电影艺术", "史诗大片", "暗黑", "涂鸦",
                 "漫画场景", "特写", "油画", "水彩画", "素描", "卡通画", "浮世绘", "赛博朋克", "吉卜力", "哑光",
                 "现代中式", "相机", "CG渲染", "动漫", "霓虹游戏", "通用漫画", "Momoko", "MJ风格", "剪纸", "齐白石", "丰子恺"]

        payload = {
            "prompt": f"{prompt}",
            "guidance_scale": 10.0,
            "height": 768,
            "negative_prompts": "",
            "sampler": "ddim",
            "seed": 1024,
            "steps": 50,
            "style": random.choice(style),
            "upsample": 2,
            "width": 512
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "token": f"{token_key}"
        }

        response = requests.request("POST", url, json=payload, headers=headers)
        logger.info("开始进行绘画......")
        if response.json()['code'] == 200:

            logger.info("AI绘画完成......")
            return response.json().get('data')
        if response.json()['code'] == -6:
            logger.info("包含非法字符")
            return -6
        return ''
