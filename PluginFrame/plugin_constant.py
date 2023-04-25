# 命令关联的插件
from constants import config

directives = {}

# 命令插件索引
directives_keys = {
    "private": [],
    "group": []
}

# 插件描述
plugin_desc = {}

# 插件描述索引
plugin_desc_key = {}


manager_qq = [config.onebot.manager_qq, ]

code_qq = 1113855149

choose_data = {}


def set_choose_data(user_id, message_type, key, value):
    del_choose_data(user_id)

    choose_data[f"{user_id}"] = {
        f"{message_type}": {
            key: value
        }
    }
    return True


def get_choose_data(user_id, message_type):

    if str(user_id) in choose_data:
        if message_type in choose_data[str(user_id)]:
            return choose_data[str(user_id)][message_type]
    return {}


def del_choose_data(user_id):
    if str(user_id) in choose_data:
        choose_data.pop(str(user_id))
    return True