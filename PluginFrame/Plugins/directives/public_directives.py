from aiocqhttp import MessageSegment
from loguru import logger

import constants
from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.chace_data import set_cache, get_cache, del_cache
from PluginFrame.plugin_constant import plugin_desc, manager_qq, code_qq, get_manager_qq, add_manager_qq, \
    get_black_list, set_black_list, del_black_list
from PluginFrame.plugins_conf import registration_directive
from constants import config, botManager
from cqhttp.api import CQApiConfig
from cqhttp.request_model import GetMessage
from manager.bot import BotManager
from middlewares.ratelimit import manager as ratelimit_manager
from utils.text_to_img import to_image


@registration_directive(matching=r'^\.设置 (\w+) (\S+) 额度为 (\d+)条/小时', message_types=("private", "group"))
class SetUpQuotasPlugin(BaseComponentPlugin):
    __name__ = 'SetUpQuotasPlugin'
    desc = "设置每小时GPT额度"
    docs = ".设置 [群组/好友] [群号/QQ号] 额度为 [99]条/小时"
    permissions = ("admin",)

    async def start(self, message_parameter):

        event = message_parameter.get("event")
        # 获取正则对象
        re_obj = message_parameter.get("re_obj")
        # 获取机器人对象
        bot = message_parameter.get("bot")
        msg_type, msg_id, rate = re_obj.groups()

        if msg_type not in ["群组", "好友"]:
            return await bot.send(event, "类型异常，仅支持设定【群组】或【好友】的额度")
        if msg_id != '默认' and not msg_id.isdecimal():
            return await bot.send(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
        ratelimit_manager.update(msg_type, msg_id, int(rate))
        return await bot.send(event, "额度更新成功！")


@registration_directive(matching=r'#菜单', message_types=("private", "group"))
class MenuPlugin(BaseComponentPlugin):
    __name__ = 'MenuPlugin'

    desc = "功能菜单"
    docs = "#菜单"
    permissions = ("all",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        # 获取机器人对象
        bot = message_parameter.get("bot")
        menu_info = '### 普通用户权限功能菜单如下：\n'
        code_menu_info = '\n### 开发者权限菜单如下：\n'
        manager_menu_info = '\n### 管理员权限菜单如下：\n'
        for key, value in plugin_desc.items():
            if not value.get('docs'):
                continue

            if event.message_type in value.get('message_types'):
                permissions = value.get('permissions')
                if not permissions or 'all' in permissions:
                    menu_info += f"- {key} -- {value.get('docs')}\n- - -\n"
                    continue
                if "admin" in permissions:
                    if event.user_id in get_manager_qq():
                        manager_menu_info += f"- {key} -- {value.get('docs')}\n- - -\n"
                        continue
                if 'code' in permissions:
                    if event.user_id == code_qq:
                        code_menu_info += f"- {key} -- {value.get('docs')}\n- - -\n"
                    continue
                if event.user_id in permissions:
                    menu_info += f"- {key} -- {value.get('docs')}\n- - -\n"
                    continue
        image_info = await to_image(
            menu_info+manager_menu_info+code_menu_info,
            qr_code="https://file.52xiaobei.cn/bFxrC3Wet70up4PB4sFV1FCXHCsud4JA/logo.png"
        )
        resp = MessageSegment.image(f"base64://{image_info.base64}")
        await bot.send(event, resp)


# 添加管理员
@registration_directive(matching=r'#添加管理员(\d+|\[CQ:at,qq=(\d+)\])', message_types=("private", "group"))
class AddManagerPlugin(BaseComponentPlugin):
    __name__ = 'AddManagerPlugin'

    desc = "添加机器人管理员"
    docs = "#添加管理员[@群员 | QQ号]"
    permissions = ("code",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        # 获取正则对象
        re_obj = message_parameter.get("re_obj")
        # 获取机器人对象
        bot = message_parameter.get("bot")
        friends_qq, at_qq = re_obj.groups()

        if at_qq:
            if int(at_qq) not in get_manager_qq():
                add_manager_qq(int(at_qq))
            else:
                await bot.send(event, "已经是管理员！")
                return
        else:
            if int(friends_qq) not in get_manager_qq():
                add_manager_qq(int(friends_qq))
            else:
                await bot.send(event, "已经是管理员！")
                return

        await bot.send(event, "添加成功！")
        return True


@registration_directive(matching=r'#禁用(\d+|\[CQ:at,qq=(\d+)\])', message_types=("private", "group"))
class AddFriendBlacklistPlugin(BaseComponentPlugin):
    __name__ = 'AddFriendBlacklistPlugin'

    desc = "禁用某QQ使用机器人"
    docs = "#禁用[@群员 | QQ号]"
    permissions = ("admin", )

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        # 获取正则对象
        re_obj = message_parameter.get("re_obj")
        # 获取机器人对象
        bot = message_parameter.get("bot")
        friends_qq, at_qq = re_obj.groups()

        if at_qq:
            if int(at_qq) == code_qq:
                await bot.send(event, "禁止将开发者添加黑名单！")
                return
            if int(at_qq) in get_manager_qq():
                if event.user_id == code_qq:
                    set_black_list("private", int(at_qq))
                    return
                else:
                    await bot.send(event, "无权限将管理员加入黑名单！")
                    return
            set_black_list("private", int(at_qq))
        else:
            if int(friends_qq) == code_qq:
                await bot.send(event, "禁止将开发者添加黑名单！")
                return
            if int(friends_qq) in get_manager_qq():
                if event.user_id == code_qq:
                    set_black_list("private", int(friends_qq))
                    return
                else:
                    await bot.send(event, "无权限将管理员加入黑名单！")
                    return
            set_black_list("private", int(friends_qq))

        await bot.send(event, "添加成功！")
        return True


@registration_directive(matching=r'#解禁(\d+|\[CQ:at,qq=(\d+)\])', message_types=("private", "group"))
class DelFriendBlacklistPlugin(BaseComponentPlugin):
    __name__ = 'DelFriendBlacklistPlugin'

    desc = "移除禁用某QQ使用机器人"
    docs = "#解禁[@群员 | QQ号]"
    permissions = ("admin", )

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        # 获取正则对象
        re_obj = message_parameter.get("re_obj")
        # 获取机器人对象
        bot = message_parameter.get("bot")
        friends_qq, at_qq = re_obj.groups()

        if at_qq:
            if int(at_qq) in get_manager_qq():
                if event.user_id == code_qq:
                    del_black_list("private", int(at_qq))
                else:
                    await bot.send(event, "无权限将管理员移除黑名单！")
                    return
            del_black_list("private", int(at_qq))
        else:
            if int(friends_qq) in get_manager_qq():
                if event.user_id == code_qq:
                    del_black_list("private", int(friends_qq))
                else:
                    await bot.send(event, "无权限将管理员移除黑名单！")
                    return
            del_black_list("private", int(friends_qq))

        await bot.send(event, "移除成功！")
        return True


@registration_directive(matching=r'#重启', message_types=("private", "group"))
class RebootPlugin(BaseComponentPlugin):
    __name__ = 'RebootPlugin'
    desc = ""
    docs = ""
    permissions = ("admin", )

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")

        constants.config = config.load_config()
        config.scan_presets()
        await bot.send(event, "配置文件重新载入完毕！")
        await bot.send(event, "重新登录账号中，详情请看控制台日志……")
        constants.botManager = BotManager(config)
        await botManager.login()
        await bot.send(event, "登录结束")


@registration_directive(matching=r'^\[CQ:reply,id=(-\d+|\d+)\](\[CQ:at,qq=(\d+)\]|)(| )撤回',
                        message_types=("private", "group"))
class MessageWithdrawPlugin(BaseComponentPlugin):
    __name__ = 'MessageWithdrawPlugin'
    desc = "消息撤回"
    docs = ''
    permissions = ("all",)

    async def start(self, message_parameter):

        message_id, _, qq, _ = message_parameter.get("re_obj").groups()
        try:
            await self.del_wait(message_id)
        except Exception as e:
            logger.debug(f"消息撤回失败---{e}")


@registration_directive(matching=r'#设置入群提示语 (.*)', message_types=("group", ))
class GroupPromptPlugin(BaseComponentPlugin):
    __name__ = 'GroupPromptPlugin'
    desc = "设置入群提示语 【提示语文本】"
    docs = ''
    permissions = ("admin",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        re_obj = message_parameter.get("re_obj")
        text = re_obj.group(1)

        set_cache(str(event.group_id), text)

        await bot.send(event, "添加成功")


@registration_directive(matching=r'#删除入群提示语', message_types=("group", ))
class DelGroupPromptPlugin(BaseComponentPlugin):
    __name__ = 'DelGroupPromptPlugin'
    desc = "删除入群提示语"
    docs = ''
    permissions = ("admin",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        if get_cache(str(event.group_id)):
            del_cache(str(event.group_id))

        await bot.send(event, "删除成功")


@registration_directive(matching=r'#开启退群提醒', message_types=("group", ))
class GroupExitPlugin(BaseComponentPlugin):
    __name__ = 'GroupExitPlugin'
    desc = "开启退群提醒"
    docs = ''
    permissions = ("admin",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")

        infos = get_cache("group_exit") or []
        if event.group_id not in infos:
            infos.append(event.group_id)
            set_cache("group_exit", infos)
        await bot.send(event, "添加成功")


@registration_directive(matching=r'#关闭退群提醒', message_types=("group", ))
class DelGroupExitPlugin(BaseComponentPlugin):
    __name__ = 'DelGroupExitPlugin'
    desc = "关闭退群提醒"
    docs = ''
    permissions = ("admin",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        infos = get_cache("group_exit") or []
        if event.group_id in infos:
            infos.pop(infos.index(event.group_id))
            set_cache("group_exit", infos)

        await bot.send(event, "删除成功")
