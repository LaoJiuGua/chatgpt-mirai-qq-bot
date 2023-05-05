import re
import aiocqhttp
from aiocqhttp import MessageSegment
from graia.amnesia.message import MessageChain
from graia.ariadne.message.element import Plain, Image, At
from loguru import logger
from PluginFrame.PluginManager import PluginManager
from PluginFrame.plugin_constant import code_qq, init_manager_qq, get_manager_qq, get_black_list
from PluginFrame.plugins_conf import PluginMatching
from TimedTasks import aioscheduler
from constants import config
from TimedTasks.queue_message import queue
bot = aiocqhttp.CQHttp(api_root=config.onebot.api_root)


class MessageDispose:

    plugin_parameter = {}

    async def dispose(self, event: aiocqhttp.Event):
        if event.type in ('message', "message_sent"):
            if event.detail_type == "private" and event.type == "message":
                if event.user_id in get_black_list("private"):
                    return
                return await self.__private_message_dispose(event)

            if event.detail_type == "group" and event.type == "message":
                if event.group_id in get_black_list("group") or event.user_id in get_black_list("private"):
                    if event.user_id in get_manager_qq() and "#解禁此群" == event.message:
                        return await self.__group_message_dispose(event)
                await self.__group_message_dispose(event)

    async def __private_message_dispose(self, event):
        re_obj, ma_obj = await PluginMatching.find_matching(event.message, 'private')

        if not ma_obj:
            return

        if plugin := await PluginManager.get_plugin_by_name(ma_obj.plugin_name):
            # 权限认证
            is_per = await self.__permission_authentication(plugin, event)
            if not is_per:
                message = MessageSegment.reply(event.get("message_id")).__add__(
                    MessageSegment.text('您没有权限执行这个操作'))
                return await bot.send(event, message)
                # 传递参数
            self.plugin_parameter["event"] = event
            self.plugin_parameter["bot"] = bot
            self.plugin_parameter["re_obj"] = re_obj
            self.plugin_parameter["ma_obj"] = ma_obj
            # 执行插件开始方法
            logger.info(f"执行插件：{ma_obj.plugin_name}")
            await plugin.start(self.plugin_parameter)
            # queue.put({'func': plugin.start, 'args': (self.plugin_parameter,)})
            # aioscheduler.add_job(func=plugin.start, args=(self.plugin_parameter, ))
        return

    async def __group_message_dispose(self, event):

        re_obj, ma_obj = await PluginMatching.find_matching(event.message, 'group')

        if not ma_obj:
            return

        if plugin := await PluginManager.get_plugin_by_name(ma_obj.plugin_name):
            # 权限认证
            is_per = await self.__permission_authentication(plugin, event)
            if not is_per:
                message = MessageSegment.reply(event.get("message_id")).__add__(
                    MessageSegment.text('您没有权限执行这个操作'))
                return await bot.send(event, message)
            # 传递参数
            self.plugin_parameter["event"] = event
            self.plugin_parameter["re_obj"] = re_obj
            self.plugin_parameter["bot"] = bot
            self.plugin_parameter["ma_obj"] = ma_obj
            # 执行插件开始方法
            logger.info(f"执行插件：{ma_obj.plugin_name}")
            # aioscheduler.add_job(func=plugin.start, args=(self.plugin_parameter, ))
            # queue.put({'func': plugin.start, 'args': (self.plugin_parameter,)})
            await plugin.start(self.plugin_parameter)
        return

    @staticmethod
    async def __permission_authentication(plugin, event):
        if hasattr(plugin, "permissions"):
            if not plugin.permissions:
                return True
            if "all" in plugin.permissions:
                return True
            elif 'code' in plugin.permissions:
                if event.user_id != code_qq:
                    return False
            elif 'admin' in plugin.permissions:
                if event.user_id not in get_manager_qq():
                    return False
            else:
                if event.user_id in plugin.permissions:
                    return True
                else:
                    return False
        return True


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
    init_manager_qq()
    return await bot.run_task(host=config.onebot.reverse_ws_host, port=config.onebot.reverse_ws_port)


bot.on_message()(MessageDispose().dispose)
