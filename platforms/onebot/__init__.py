import re

import aiocqhttp
from graia.amnesia.message import MessageChain
from graia.ariadne.message.element import Plain, Image, At
from loguru import logger

from PluginFrame.PluginManager import PluginManager
from PluginFrame.plugins_conf import PluginMatching
from constants import config, botManager

bot = aiocqhttp.CQHttp(api_root=config.onebot.cq_http_url)


class MessageDispose:

    plugin_parameter = {}

    async def dispose(self, event: aiocqhttp.Event):
        if event.type in ('message', "message_sent"):
            if event.detail_type == "private" and event.type == "message":
                await self.__private_message_dispose(event)
            if event.detail_type == "group" and event.type == "message":
                await self.__group_message_dispose(event)

    async def __private_message_dispose(self, event):
        re_obj, ma_obj = PluginMatching.find_matching(event.message, 'private')

        if not ma_obj:
            return

        if plugin := PluginManager.get_plugin_by_name(ma_obj.plugin_name):

            # 传递参数
            self.plugin_parameter["event"] = event
            self.plugin_parameter["re_obj"] = re_obj
            self.plugin_parameter["ma_obj"] = ma_obj
            # 执行插件开始方法
            logger.info(f"执行插件：{ma_obj.plugin_name}")
            return await plugin.start(self.plugin_parameter)
        return

    async def __group_message_dispose(self, event):

        re_obj, ma_obj = PluginMatching.find_matching(event.message, 'group')

        if not ma_obj:
            return

        if plugin := PluginManager.get_plugin_by_name(ma_obj.plugin_name):

            # 传递参数
            self.plugin_parameter["event"] = event
            self.plugin_parameter["re_obj"] = re_obj
            self.plugin_parameter["ma_obj"] = ma_obj
            # 执行插件开始方法
            logger.info(f"执行插件：{ma_obj.plugin_name}")
            return await plugin.start(self.plugin_parameter)
        return


def transform_message_chain(text: str) -> MessageChain:
    pattern = r"\[CQ:(\w+),([^\]]+)\]"
    matches = re.finditer(pattern, text)

    message_classes = {
        "text": Plain,
        "image": Image,
        "at": At,
        # Add more message classes here
    }

    messages = []
    start = 0
    for match in matches:
        cq_type, params_str = match.groups()
        params = dict(re.findall(r"(\w+)=([^,]+)", params_str))
        if message_class := message_classes.get(cq_type):
            text_segment = text[start:match.start()]
            if text_segment and not text_segment.startswith('[CQ:reply,'):
                messages.append(Plain(text_segment))
            if cq_type == "at":
                params["target"] = int(params.pop("qq"))
            messages.append(message_class(**params))
            start = match.end()
    if text_segment := text[start:]:
        messages.append(Plain(text_segment))

    return MessageChain(*messages)


async def start_task():
    """|coro|
    以异步方式启动
    """
    PluginManager.load_all_plugin()
    return await bot.run_task(host=config.onebot.reverse_ws_host, port=config.onebot.reverse_ws_port)


bot.on_message()(MessageDispose().dispose)
