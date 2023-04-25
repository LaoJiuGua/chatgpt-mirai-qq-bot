import base64
import io
import re
from io import BytesIO
import requests
from loguru import logger
from PIL import Image
from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugin_constant import choose_data, set_choose_data, get_choose_data, del_choose_data
from PluginFrame.plugins_conf import registration_directive
from cqhttp.api import CQApiConfig
from cqhttp.request_model import MessageSegment, SendPrivateMsgRequest, SendGroupMsgRequest, GetMessage


@registration_directive(matching=r'^#(美女|放松心情|轻松一刻)', message_types=("private", "group"))
class DouYinBellePlugin(BaseComponentPlugin):
    __name__ = 'DouYinBellePlugin'
    desc = "抖音MM短视频"
    docs = '#美女 / #放松心情 / #轻松一刻'
    permissions = ("all",)

    async def start(self, message_parameter):

        message_info = message_parameter.get("event")
        sender = message_info.sender
        message = MessageSegment.video(self.get_girl_url())
        if message_info.get("message_type") == "group":
            await SendGroupMsgRequest(group_id=message_info.get("group_id"), message=message).send_request(
                CQApiConfig.message.send_group_msg.Api
            )
        elif message_info.get("message_type") == "private":
            await SendPrivateMsgRequest(user_id=sender.get("user_id"), message=message).send_request(
                CQApiConfig.message.send_private_msg.Api
            )

    @staticmethod
    def get_girl_url():
        resp = requests.get("http://xin-hao.top/sqlWork/randomDouyin")
        try:
            url = resp.history[1].url
        except:
            url = "http://xin-hao.top/sqlWork/randomDouyin"
        logger.info("取到的url为：{}".format(url))
        return url


@registration_directive(matching=r'^#(ping|Ping) (.*)', message_types=("private", "group"))
class PingHostPlugin(BaseComponentPlugin):
    __name__ = 'PingHostPlugin'
    desc = "Ping域名"
    docs = '#Ping / #ping [baidu.com]'
    permissions = ("admin",)

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


@registration_directive(matching=r'^#舔狗', message_types=("private", "group"))
class AnimeWallpapersPlugin(BaseComponentPlugin):
    __name__ = 'AnimeWallpapersPlugin'
    desc = "舔狗日记"
    docs = '#舔狗'
    permissions = ("all",)

    async def start(self, message_parameter):

        message_info = message_parameter.get("event")
        sender = message_info.sender
        if message_info.get("message_type") == "group":
            logger.info(
                f"收到群组({message_info.get('group_id')})消息：{sender.get('nickname')}({sender.get('user_id')})---->{message_info.get('message')}"
            )
            wait_info = await self.send_wait(self.send_group_msg, group_id=message_info.get("group_id"))(
                message_info.get("message_id"), "请稍后..."
            )
            await self.del_wait(wait_info.get("message_id"))
            data = MessageSegment.reply(message_info.get('message_id')).__add__(
                MessageSegment.text(self.get_tiangou_info())
            )
            await self.send(self.send_group_msg, user_id=message_info.get("group_id"))(
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
                MessageSegment.text(self.get_tiangou_info())
            )

            await self.send(self.send_private_msg, user_id=message_info.get("user_id"))(
                message=str(data)
            )

    @staticmethod
    def get_tiangou_info():
        try:
            resp = requests.get("https://v.api.aa1.cn/api/tiangou/", timeout=10)
            text = re.findall(r"<p>(.*?)</p>", resp.text)
        except:
            text = ["接口似乎出现问题了！！"]
        return text[0]


@registration_directive(matching=r'^#今日热点', message_types=("private", "group"))
class TodayHotSpotPlugin(BaseComponentPlugin):
    __name__ = 'TodayHotSpotPlugin'
    desc = "今日热点"
    docs = '#今日热点'
    permissions = ("admin",)

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


@registration_directive(matching=r'^\[CQ:reply,id=(-\d+|\d+)\](\[CQ:at,qq=(\d+)\]|)(| )(放大|缩小)(\d{1})倍',
                        message_types=("private", "group"))
class ImageVariationPlugin(BaseComponentPlugin):
    __name__ = 'ImageVariationPlugin'
    desc = "图片放大/缩小"
    docs = '引用图片消息 [放大/缩小][1-9]倍 【群内去掉At】'
    permissions = ("all",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        message_id, _, qq, _, im_type, number = message_parameter.get("re_obj").groups()
        info = await GetMessage(message_id=message_id).send_request(api=CQApiConfig.message.get_msg.Api)
        if not info: return
        message_data = info.get("message")
        url = re.match(r"(| )\[CQ:image.*url=(.*)]", message_data).group(2)
        image_data, fmt = self.download_image(url)
        img_b64 = self.image_zoom(image_data, number, im_type, fmt=fmt)
        if not img_b64:
            await bot.send(event, MessageSegment.reply(event.message_id).__add__(
                MessageSegment.text("图片不合法")
            ))

        message = MessageSegment.reply(event.message_id).__add__(
            MessageSegment.image(file=f"base64://{img_b64}", type=fmt)
        )
        await bot.send(event, message)

    def download_image(self, url):
        try:
            response = requests.get(url)
            fmt = response.headers.get("Content-Type", 'image/jpeg')
            fmt = fmt.split("/")[1]
            with Image.open(BytesIO(response.content)) as _img:
                image_data = self.image_to_base64(_img, fmt=fmt)
            return image_data, fmt
        except:
            return None

    @staticmethod
    def image_to_base64(img, fmt='png'):
        output_buffer = BytesIO()
        img.save(output_buffer, format=fmt)
        byte_data = output_buffer.getvalue()
        base64_str = base64.b64encode(byte_data).decode('utf-8')
        return base64_str

    def image_zoom(self, imgdata, scale=1, scale_type=None, fmt='png'):
        buffer = io.BytesIO()
        imgdata = base64.b64decode(imgdata)
        img = Image.open(io.BytesIO(imgdata))
        if scale_type == "缩小":
            new_img = img.resize((img.size[0]//int(scale), img.size[1]//int(scale)))
        elif scale_type == "放大":
            new_img = img.resize((img.size[0] * int(scale), img.size[1] * int(scale)))
        else:
            return
        new_img.save(buffer, format=fmt)
        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return img_b64


@registration_directive(matching=r'#点歌(| )(.*)', message_types=("private", "group"))
class MusicPlugin(BaseComponentPlugin):
    __name__ = 'MusicPlugin'
    desc = "点歌系统（网易云）"
    docs = '#点歌 [歌曲名称]'
    permissions = ("admin",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        _, music_name = message_parameter.get("re_obj").groups()

        wait_info = await bot.send(event, MessageSegment.reply(event.get("message_id")).__add__(
            MessageSegment.text('请稍后...')
        ))
        print(wait_info)
        r_id_info, r_ids = self.get_music(music_name)

        await self.del_wait(wait_info.get("message_id"))

        if not r_id_info:
            await bot.send(event, "接口似乎出现了问题！！")
            return

        r_id_info.insert(0, MessageSegment.node_custom(
            nickname="北.", user_id=1113855149,
            content=MessageSegment.text("请输入-【序号】选择歌曲！")
        ))

        if event.get("message_type") == "group":

            message_info=await self.send(self.send_group_node_msg, group_id=event.get("group_id"))(
                    messages=r_id_info
                )
            set_choose_data(
                event.user_id, event.message_type, 'mus', {"r_ids": r_ids, "message_id": message_info.get("message_id")}
            )

        elif event.get("message_type") == "private":

            message_info = await self.send(self.send_private_node_msg, user_id=event.get("user_id"))(
                messages=r_id_info
            )
            set_choose_data(
                event.user_id, event.message_type, 'mus', {"r_ids": r_ids, "message_id": message_info.get("message_id")}
            )

    def get_music(self, name):
        _list = []
        r_ids = []
        try:
            res = requests.get(
                f"https://api.pearktrue.cn/api/music/search.php?name={name}&type=netease&page=1", timeout=10
            )
            music_data = res.json().get("data", []) or []
            for index, music in enumerate(music_data):
                id = re.fullmatch("http://music.163.com/song/media/outer/url\?id=(.*).mp3", music.get('playurl'))
                if not id:
                    continue
                r_id = id.group(1)
                r_ids.append(r_id)
                message = MessageSegment.node_custom(
                    nickname="北.", user_id=1113855149,
                    content=f"""{MessageSegment(type_="reply", data={"text": "序号："+str(index), "qq": 1113855149})}歌名：《{music.get('title')}》\n演唱：{music.get('author')}"""
                )
                _list.append(message)
            return _list, r_ids
        except:
            return False


@registration_directive(matching=r'-(| )(\d+)', message_types=("private", "group"))
class ChoosePlugin(BaseComponentPlugin):
    __name__ = 'ChoosePlugin'
    desc = ""
    docs = ''
    permissions = ("all",)

    async def start(self, message_parameter):
        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        _, choose_id = message_parameter.get("re_obj").groups()
        _data = get_choose_data(event.user_id, event.message_type)
        if 'mus' in _data:
            await self.mus_send(event, choose_id, _data, bot)
        return

    async def mus_send(self, event, choose_id, _data, bot):
        mus = _data.get("mus", {}) or {}
        if not mus:
            return
        r_ids = mus.get('r_ids')
        if not r_ids:
            return
        try:
            id_ = r_ids[int(choose_id)]
        except:
            await bot.send(event, "歌曲序号不正确！重新选择")
            return False
        message = MessageSegment.music(type_='163', id_=id_)
        await self.del_wait(mus.get("message_id", ''))
        await bot.send(event, message)
        del_choose_data(event.user_id)
        return message
