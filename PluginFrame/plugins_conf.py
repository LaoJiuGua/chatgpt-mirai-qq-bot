import re
import dataclasses
from loguru import logger

from PluginFrame.plugin_constant import directives_keys, directives, plugin_desc, plugin_desc_key


class DirectivesPluginMeta(type):

    def __init__(cls, _class_name, _base, _class_obj, **kwargs):
        for key, value in _class_obj.items():
            if isinstance(value, DirectivesField):
                if value.matching in directives_keys:
                    raise ValueError(f"指令 {value.matching} 已存在")
                directives[key] = value
                for message_type in value.message_types:
                    directives_keys[message_type].append(value.matching)
        super(DirectivesPluginMeta, cls).__init__(_class_name, _base, _class_obj, **kwargs)

    @property
    def directives(self):
        return directives

    async def find_matching(self, matching, message_type):
        directive, match_obj = None, None
        for key, value in directives.items():
            if re.fullmatch(value.matching, matching) and message_type in value.message_types:
                match_obj = re.fullmatch(value.matching, matching)
                directive = value
        return match_obj, directive

    def __setattr__(cls, key, value):
        for message_type in value.message_types:
            if value.matching in directives_keys[message_type]:
                raise ValueError(f"指令 {value.matching} 已存在 {message_type}")
        directives[key] = value

        for message_type in value.message_types:
            directives_keys[message_type].append(value.matching)

        if value.desc:
            plugin_desc[value.desc] = dict(
                docs=value.docs,
                plugin_name=value.plugin_name,
                permissions=value.permissions,
                message_types=value.message_types,
            )
            plugin_desc_key[value.desc] = value.plugin_name

        return True


@dataclasses.dataclass
class DirectivesField:
    matching: str = '.*'
    plugin_name: str = None
    message_types: tuple = ("private", "group")
    desc: str = ''
    docs: str = ''
    permissions: tuple = ("all",)


class PluginMatching(metaclass=DirectivesPluginMeta):
    ...


def registration_directive(matching: str, message_types: tuple):
    def wrapper(cls):
        plugin_name = cls.__name__
        desc, docs, permissions = '', '', ("all",)
        if hasattr(cls, "desc"):
            desc = cls.desc
        if hasattr(cls, "docs"):
            docs = cls.docs
        if hasattr(cls, "permissions"):
            permissions = cls.permissions

        setattr(
            PluginMatching,
            plugin_name,
            DirectivesField(
                matching=matching, plugin_name=plugin_name, message_types=message_types,
                desc=desc, docs=docs, permissions=permissions
            )
        )
        logger.info(f"注册{','.join(message_types)}指令：{plugin_name} - {matching}")
    return wrapper





