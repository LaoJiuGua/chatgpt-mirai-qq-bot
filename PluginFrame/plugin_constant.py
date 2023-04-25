# 命令关联的插件
import json
import os
import pickle
from constants import config

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def init_manager_qq():
    with open(os.path.join(path, "data/manager_qq.json"), 'wb') as f:
        pickle.dump(manager_qq, f)
    return True


def add_manager_qq(qq):
    manager_qq.append(qq)

    with open(os.path.join(path, "data/manager_qq.json"), 'wb') as f:
        pickle.dump(manager_qq, f)

    return True


def get_manager_qq():
    global manager_qq
    if os.path.isfile(os.path.join(path, "data/manager_qq.json")):
        with open(os.path.join(path, "data/manager_qq.json"), 'rb') as f:
            manager_qq = pickle.load(f)
    return manager_qq


def set_choose_data(user_id, message_type, key, value):
    del_choose_data(user_id)

    choose_data[f"{user_id}"] = {
        f"{message_type}": {
            key: value
        }
    }
    with open(os.path.join(path, "data/choose_data.json"), 'w') as f:
        json.dump(choose_data, f)
    return True


def get_choose_data(user_id, message_type):
    global choose_data

    if os.path.isfile(os.path.join(path, "data/choose_data.json")):
        with open(os.path.join(path, "data/choose_data.json"), 'r') as f:
            choose_data = json.load(f)

    if str(user_id) in choose_data:
        if message_type in choose_data[str(user_id)]:
            return choose_data[str(user_id)][message_type]
    return {}


def del_choose_data(user_id):
    if str(user_id) in choose_data:
        choose_data.pop(str(user_id))

    with open(os.path.join(path, "data/choose_data.json"), 'w') as f:
        json.dump(choose_data, f)

    return True


