import json
import os
import random
import time

from aiocqhttp import MessageSegment

from PluginFrame.Plugins import BaseComponentPlugin
from PluginFrame.plugin_constant import set_choose_data, get_choose_data, del_choose_data
from PluginFrame.plugins_conf import registration_directive

tor_path = os.path.dirname(os.path.abspath(__file__))


@registration_directive(matching=r'^#抽([1-3])张?(塔罗牌|大阿(尔)?卡纳|小阿(尔)?卡纳)$', message_types=("private", "group"))
class TarotPlugin(BaseComponentPlugin):
    __name__ = 'TarotPlugin'
    desc = "塔罗牌"
    docs = '#抽[1-3]张塔罗牌'
    permissions = ("all",)

    # 插件内
    bed = "https://gitcode.net/shudorcl/zbp-tarot/-/raw/master/"
    tarots_data = {}
    reasons = ["您抽到的是~", "锵锵锵，塔罗牌的预言是~", "诶，让我看看您抽到了~"]
    position = ["『正位』", "『逆位』"]
    reverse = ["", "Reverse/"]

    async def start(self, message_parameter):

        event = message_parameter.get("event")
        bot = message_parameter.get("bot")
        re_obj = message_parameter.get("re_obj")
        match, card_type, _, _ = re_obj.groups()

        start = 22 if "小" in card_type else 0
        length = 55 if "小" in card_type else 22

        if not self.tarots_data:
            self.load_tarots()
        wait_info = await bot.send(event, MessageSegment.reply(event.get("message_id")).__add__(
            MessageSegment.text(random.choice(self.reasons))
        ))

        card_list_infos = []
        for i in range(int(match)):
            num = random.randint(start, length)
            card = self.tarots_data.get(str(num))
            p = random.randint(0, 1)
            name = card.get("name")
            info = card.get("info")
            reverse = self.reverse[p]
            description = info.get("reverseDescription") if reverse else info.get("description")
            img_url = self.bed + reverse + info.get("imgUrl")

            text = f"牌名：\n{name}{self.position[p]}\n其释义为：\n{description}"
            message = MessageSegment.node_custom(
                nickname="北.", user_id=1113855149,
                content=f"""{MessageSegment.image(file=img_url)}\n{text}"""
            )
            card_list_infos.append(message)

        await self.del_wait(wait_info.get("message_id"))

        if event.message_type == "group":
            message_info = await self.send(self.send_group_node_msg, group_id=event.get("group_id"))(
                    messages=card_list_infos
                )
        elif event.get("message_type") == "private":
            message_info = await self.send(self.send_private_node_msg, user_id=event.get("user_id"))(
                messages=card_list_infos
            )

    def load_tarots(self):
        with open(os.path.join(tor_path, "data/tarots.json"), "r", encoding="utf-8") as tarots:
            self.tarots_data = json.loads(tarots.read())


