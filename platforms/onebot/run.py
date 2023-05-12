from PluginFrame.PluginManager import PluginManager
from PluginFrame.chace_data import init_cache
from PluginFrame.plugin_constant import init_manager_qq
from constants import config
from platforms.onebot import bot
from platforms.onebot.message_dispose import MessageDispose
from platforms.onebot.notice_dispose import NoticeDispose

bot.on_message()(MessageDispose().dispose)
bot.on_notice()(NoticeDispose().dispose)


async def start_task():
    """|coro|
    以异步方式启动
    """
    PluginManager.load_all_plugin()
    init_manager_qq()
    init_cache()
    return await bot.run_task(host=config.onebot.reverse_ws_host, port=config.onebot.reverse_ws_port)
