from aiocqhttp import MessageSegment

from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugins_conf import registration_directive
from utils.html_to_image import html_to_png
from utils.text_to_img import to_image

key = "d73IGg5Nn4hXl0a8CzHeUrGUgV"

sj = {
    '超市': {'url': 'http://api.caonm.net/api/chaop/j?qq=', 'liang': 2},
    '超': {'url': 'https://api.caonm.net/api/chao/api?qq=', 'liang': 2},
    '没业务': {'url': 'http://api.caonm.net/api/yewu/y?qq=', 'liang': 0},
    '美女电视': {'url': 'http://api.caonm.net/api/dsjp/j?qq=', 'liang': 0},
    '背刺': {'url': 'http://api.caonm.net/api/bei/b?qq=', 'liang': 2},
    '处男证书': {'url': 'http://api.caonm.net/api/zhen/c30?qq=', 'liang': 0},
    '泡妞证书': {'url': 'http://api.caonm.net/api/zhen/c14?qq=', 'liang': 0},
    '滚粗QQ': {'url': 'http://api.caonm.net/api/gun/index?qq=', 'liang': 0},
    # '日记': {'url': 'https://api.caonm.net/api/tgrj/j?qq=1113855149&msg=cnm&key=d73IGg5Nn4hXl0a8CzHeUrGUgV', 'liang': 0},
}


@registration_directive(matching=r'(.*)\[CQ:at,qq=(\d+)\]( |)', message_types=("group", ))
class EmoticonPlugin(BaseComponentPlugin):
    __name__ = 'EmoticonPlugin'
    plu_name = '表情包插件'
    desc = "QQ表情包生成"
    docs = '表情包名称[@群友]'
    permissions = ("all",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        re_obj = message_parameter.get("re_obj")
        emo_type, at_qq, _ = re_obj.groups()

        sj_info = sj.get(emo_type)
        if not sj_info:
            return

        mo_url = sj_info.get("url")
        liang = sj_info.get("liang")
        if liang == 1:
            url = mo_url+str(event.user_id)+f"&qq={str(at_qq).strip()}&key={key}"
        elif liang == 2:
            url = mo_url+str(event.user_id)+f"&qq2={str(at_qq).strip()}&key={key}"
        elif liang == 3:
            url = mo_url + str(event.user_id) + f"&cqq={str(at_qq).strip()}&key={key}"
        else:
            url = mo_url + str(at_qq).strip() + f"&key={key}"

        resp = MessageSegment.image(url)
        return await bot.send(event, resp)


@registration_directive(matching=r'#表情包列表', message_types=("group", ))
class EmoticonListPlugin(BaseComponentPlugin):
    __name__ = 'EmoticonListPlugin'
    plu_name = '表情包插件'
    desc = "表情包列表"
    docs = '#表情包列表'
    permissions = ("all",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        image_base61 = html_to_png("emoticon", sj)
        resp = MessageSegment.image(f"base64://{image_base61}")
        await bot.send(event, resp)
