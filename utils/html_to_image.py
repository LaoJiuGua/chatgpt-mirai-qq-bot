# -*- coding:utf-8 -*-

""" 模板语言"""
import base64
import os
import shutil
from io import StringIO, BytesIO
from tempfile import NamedTemporaryFile
from PIL import Image
import imgkit
from charset_normalizer import from_bytes
from loguru import logger

# TOKEN相关的定义
TOKEN_S_BRACE = "{"
TOKEN_S_BLOCK = "%"
TOKEN_EXPRESSION_L = "{{"
TOKEN_EXPRESSION_R = "}}"
TOKEN_BLOCK_L = "{%"
TOKEN_BLOCK_R = "%}"
TOKEN_KEY_SET = "set"
TOKEN_KEY_RAW = "raw"
TOKEN_KEY_IF = "if"
TOKEN_KEY_ELIF = "elif"
TOKEN_KEY_ELSE = "else"
TOKEN_KEY_FOR = "for"
TOKEN_KEY_WHILE = "while"
TOKEN_KEY_END = "end"
TOKEN_KEY_BREAK = "break"
TOKEN_KEY_CONTINUE = "continue"
TOKEN_SPACE = " "
TOKEN_COLON = ":"
# Token标记 {{}} {% %}
TOKEN_FLAG_SET = {TOKEN_S_BRACE, TOKEN_S_BLOCK}
# 简单的语句
TOKEN_KEY_SET_SIMPLE_EXPRESSION = {TOKEN_KEY_SET, TOKEN_KEY_RAW}
# 前置条件
TOKEN_KEY_PRE_CONDITION = {
    # end 必须在if/elif/else/for/while 后面
    TOKEN_KEY_END: {TOKEN_KEY_IF, TOKEN_KEY_ELIF, TOKEN_KEY_ELSE,
                    TOKEN_KEY_FOR, TOKEN_KEY_WHILE},
    # elif 必须在if 后面
    TOKEN_KEY_ELIF: {TOKEN_KEY_IF},
    # else 必须在if/elif 后面
    TOKEN_KEY_ELSE: {TOKEN_KEY_IF, TOKEN_KEY_ELIF, TOKEN_KEY_FOR, TOKEN_KEY_WHILE},
}
# 循环语句
TOKEN_KEY_LOOP = {TOKEN_KEY_WHILE, TOKEN_KEY_FOR}
# 循环的控制break continue
TOKEN_KEY_LOOP_CTRL = {TOKEN_KEY_BREAK, TOKEN_KEY_CONTINUE}


class ParseException(Exception):
    pass


class TemplateCode(object):
    def __init__(self):
        self.codeTrees = {"parent": None, "nodes": []}
        self.cursor = self.codeTrees
        self.compiled_code = None

    def create_code(self):
        """创建一个代码子块"""
        child_codes = {"parent": self.cursor, "nodes": []}
        self.cursor["nodes"].append(child_codes)
        self.cursor = child_codes

    def close_code(self):
        """ 关闭一个代码子块 """
        assert self.cursor["parent"] is not None, "overflow"
        self.cursor = self.cursor["parent"]

    def append_text(self, text):
        """ 添加文本 """
        # 排除空行
        self.cursor["nodes"].append("_add(%r)" % text)

    def append_express(self, express, raw=False):
        """ 表达式 """
        if raw:
            temp_exp = "_t_exp = _str_(%s)" % express
        else:
            temp_exp = "_t_exp = _esc_(%s)" % express
        self.cursor["nodes"].append(temp_exp)
        self.cursor["nodes"].append("_add(_t_exp)")

    def append_statement(self, statement):
        """ 语句 """
        temp_statement = "%s" % statement
        self.cursor["nodes"].append(temp_statement)

    def reset(self):
        self.codeTrees = {"parent": None, "nodes": []}
        self.cursor = self.codeTrees
        self.compiled_code = None

    def build_code(self, filename):
        temp_code_buff = []
        self.write_buff_with_indent(temp_code_buff, "def _template_render():", 0)
        self.write_buff_with_indent(temp_code_buff, "_codes = []", 4)
        self.write_buff_with_indent(temp_code_buff, "_add = _codes.append", 4)
        self.write_codes(temp_code_buff, self.codeTrees, 4)
        self.write_buff_with_indent(temp_code_buff, "return ''.join(_codes)", 4)
        temp_code = "".join(temp_code_buff)
        self.compiled_code = compile(temp_code,filename, "exec", dont_inherit=True)

    def write_codes(self, code_buff, codes, indent):
        for node in codes.get("nodes", []):
            if isinstance(node, dict):
                self.write_codes(code_buff, node, indent+4)
            else:
                self.write_buff_with_indent(code_buff, node, indent)

    def generate(self, **kwargs):
        temp_namespace = {}
        temp_namespace['_str_'] = self.to_utf8
        temp_namespace['_esc_'] = self.to_safe_utf8
        temp_namespace.update(kwargs)
        exec(self.compiled_code, temp_namespace)
        return temp_namespace['_template_render']()

    @staticmethod
    def write_buff_with_indent(code_buff, raw_str, indent):
        """"""
        temp = (" " * indent) + raw_str + "\n"
        code_buff.append(temp)

    @staticmethod
    def to_utf8(raw_str):
        """ 转换 """
        if isinstance(raw_str, str):
            return raw_str
        elif isinstance(raw_str, bytes):
            return raw_str.decode()
        return str(raw_str)

    @staticmethod
    def to_safe_utf8(raw_str):
        """ 过滤html转义 """
        text = TemplateCode.to_utf8(raw_str)
        return text.replace("&", "&").replace("<", "<").replace(">", ">")

class Template(object):
    """模板类"""
    def __init__(self, input_obj,filename="<string>", **namespace):
        """模板初始化"""
        self.namespace = {}
        self.namespace.update(namespace)
        # 将数据丢进去解析生成编译代码
        self.lexer = TemplateLexer(input_obj, filename)

    def render(self, **kwargs):
        """渲染模板 """
        temp_name_space = {}
        temp_name_space.update(self.namespace)
        temp_name_space.update(kwargs)
        # 执行渲染
        return self.lexer.render(**kwargs)


class TemplateLexer(object):
    """模板语法分析器 """
    def __init__(self, input_obb, filename="<string>"):
        if hasattr(input_obb, "read"):
            self.raw_string = input_obb.read()
        else:
            self.raw_string = input_obb
        self.filename = filename
        # 记录当前的位置
        self.pos = 0
        # 记录原始数据的总长度
        self.raw_str_len = len(self.raw_string)
        # 记录解析的数据
        self.code_data = TemplateCode()
        # 开始解析
        self.parse_template()

    def match(self, keyword, pos=None):
        return self.raw_string.find(keyword, pos if pos is not None else self.pos)

    def cut(self, size=-1):
        """剪取数据 size切割数据的大小，-1表示全部"""
        if size == -1:
            new_pos = self.raw_str_len
        else:
            new_pos = self.pos + size
        s = self.raw_string[self.pos: new_pos]
        self.pos = new_pos
        return s

    def remaining(self):
        """获取剩余大小 """
        return self.raw_str_len - self.pos

    def function_brace(self):
        """ 获取{{  / {% """
        skip_index = self.pos
        while True:
            index = self.match(TOKEN_S_BRACE, skip_index)  # {% {{
            # 没找到
            if index == -1:
                return None, -1
            # 末尾
            if index >= self.raw_str_len:
                return None, -1
            # 匹配类型
            next_value = self.raw_string[index + 1:index + 2]
            if next_value not in TOKEN_FLAG_SET:
                skip_index = index + 1
                # 说明不是关键类型
                continue
            brace = self.raw_string[index: index + 2]
            return brace, index
        return None, -1

    def read_content_with_token(self, index, begin_token, end_token):
        """
        读取匹配token的内容
        """
        end_index = self.match(end_token)
        if end_index == -1:
            return ParseException("{0} missing end token {1}".format(begin_token, end_token))
        # 过滤 begin_token
        self.pos = index + len(begin_token)
        content = self.cut(end_index - self.pos)
        # 去除末尾 end_token
        self.cut(len(end_token))
        return content

    def add_simple_block_statement(self, operator, suffix):
        if not suffix:
            raise ParseException("{0} missing content".format(operator))
        if operator == TOKEN_KEY_SET:
            self.code_data.append_statement(suffix)
        elif operator == TOKEN_KEY_RAW:
            self.code_data.append_express(suffix, True)
        else:
            raise ParseException("{0} is undefined".format(operator))

    def parse_template(self):
        """解析模板 """
        # TODO 检查模板文件是否更改过，如果没有则不需要重新解析
        self.code_data.reset()
        # 解析模板原文件
        self.__parse()
        # 生成编译code
        self.__compiled_code()

    def render(self, **kwargs):
        return self.code_data.generate(**kwargs)

    def __parse(self, control_operator=None, in_loop=False):
        """开始解析"""
        while True:
            if self.remaining() <= 0:
                if control_operator or in_loop:
                    raise ParseException("%s missing {%% end %%}" % control_operator)
                break
            # 读取 {{ {%
            brace, index = self.function_brace()
            # 说明没有找到
            if not brace:
                text = self.cut(index)
                self.code_data.append_text(text)
                continue
            else:
                text = self.cut(index - self.pos)
                if text:
                    self.code_data.append_text(text)

            if brace == TOKEN_EXPRESSION_L:
                content = self.read_content_with_token(index, TOKEN_EXPRESSION_L, TOKEN_EXPRESSION_R).strip()
                if not content:
                    raise ParseException("Empty Express")
                self.code_data.append_express(content)
                continue
            elif brace == TOKEN_BLOCK_L:
                content = self.read_content_with_token(index, TOKEN_BLOCK_L, TOKEN_BLOCK_R).strip()
                if not content:
                    raise ParseException("Empty block")

                # 得到表达式 for x in x ;  if x ;  elif x ;  else ;  end ;  set ;  while x ;
                operator, _, suffix = content.partition(TOKEN_SPACE)
                if not operator:
                    raise ParseException("block missing operator")

                suffix = suffix.strip()
                # 简单语句，set / raw
                if operator in TOKEN_KEY_SET_SIMPLE_EXPRESSION:
                    self.add_simple_block_statement(operator, suffix)
                elif operator in TOKEN_KEY_LOOP_CTRL:
                    if not in_loop:
                        raise ParseException("{0} must in loop block".format(operator))
                    self.code_data.append_statement(operator)
                else:
                    # 控制语句 检查匹配if 后面可以跟elif/else
                    pre_condition = TOKEN_KEY_PRE_CONDITION.get(operator, None)
                    if pre_condition:
                        # 里面就是elif/else/end
                        if control_operator not in pre_condition:
                            raise ParseException("{0} must behind with {1}".format(operator, pre_condition))
                        elif operator == TOKEN_KEY_END:
                            # 遇到{% end %}则结束
                            self.code_data.close_code()
                            return
                        else:
                            # 由于是依据if 进入 来计算elif ，因此elif与if是同级的
                            self.code_data.close_code()
                            self.code_data.append_statement(content + TOKEN_COLON)
                            self.code_data.create_code()
                            self.__parse(operator, in_loop or (operator in TOKEN_KEY_LOOP))
                            break
                    # 添加控制语句及内部语句体 if for while
                    self.code_data.append_statement(content + TOKEN_COLON)
                    self.code_data.create_code()
                    self.__parse(operator, in_loop or (operator in TOKEN_KEY_LOOP))
            else:
                raise ParseException("Unkown brace")
        return

    def __compiled_code(self):
        """生成 编译code """
        self.code_data.build_code(self.filename)


def template_html(template_name):

    base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    if not os.path.exists(os.path.join(base_path, f"assets/{template_name}/index.html")):
        raise ValueError(f"无法识别模板名称 {template_name} ！")

    with open(os.path.join(base_path, f"assets/{template_name}/index.html"), "r", encoding="utf-8") as f:
        guessed_str = f.read()
        guessed_str = guessed_str.replace("{html_path}", os.path.join(base_path, f"assets/{template_name}"))
        if not guessed_str:
            raise ValueError("无法识别文件 index.html ！")
        return guessed_str


def html_to_png(template_name, data):


    t = Template(template_html(template_name))
    html = t.render(data=data)

    base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    temp_html_file = NamedTemporaryFile(mode='w', suffix='.html', encoding='utf-8')
    imgkit_config = imgkit.config(wkhtmltoimage=shutil.which("wkhtmltoimage"))
    temp_jpg_file = NamedTemporaryFile(mode='w+b', suffix='.png')
    temp_jpg_filename = temp_jpg_file.name
    temp_jpg_file.close()
    with StringIO(html) as input_file:
        ok = False
        try:
            temp_html_file.write(html)
            # 调用imgkit将html转为图片
            ok = imgkit.from_file(
                filename=input_file, config=imgkit_config,
                options={
                    "enable-local-file-access": "",
                    "allow": os.path.join(base_path, f"assets/{template_name}"),
                    "width": 700,
                    "javascript-delay": "1000"
                },
                output_path=temp_jpg_filename
            )
            # 调用PIL将图片读取为 JPEG，RGB 格式
            img = Image.open(temp_jpg_filename, formats=['PNG']).convert('RGB')
            b = BytesIO()
            img.save(b, format="png")
            return base64.b64encode(b.getvalue()).decode()

        except Exception as e:
            logger.error("Markdown 渲染失败")



# if __name__ == "__main__":
#     data = {
#     '看这个': {'url': 'http://api.caonm.net/api/txmb/5.php?qq=', 'liang': 0},
#     '抱': {'url': 'https://api.xingzhige.com/API/baororo/?qq=', 'liang': 0},
#     '咬': {'url': 'https://api.xingzhige.com/API/bite/?qq=', 'liang': 0},
#     '登记': {'url': 'http://bh.ayud.top/img/jh.php?qq=', 'liang': 0},
#     '吞': {'url': 'https://bg.suol.cc/API/chi/?uin=', 'liang': 0},
#     '顶一顶': {'url': 'http://bg.suol.cc/API/ding/?uin=', 'liang': 0},
#     '拍': {'url': 'https://api.xingzhige.com/API/paigua/?qq=', 'liang': 0},
#     '抓': {'url': 'https://api.xingzhige.com/API/grab/?qq=', 'liang': 0},
#     '顶': {'url': 'https://api.xingzhige.com/API/dingqiu/?qq=', 'liang': 0},
#     '一起笑': {'url': 'https://api.xingzhige.com/API/LaughTogether/?qq=', 'liang': 0},
#     '搂': {'url': 'https://api.xingzhige.com/API/FortuneCat/?qq=', 'liang': 0},
#     '摇摇': {'url': 'https://api.xingzhige.com/API/DanceChickenLeg/?qq=', 'liang': 0},
#     '打拳': {'url': 'https://api.andeer.top/API/gif_beat.php?qq=', 'liang': 0},
#     '捣': {'url': 'https://api.xingzhige.com/API/pound/?qq=', 'liang': 0},
#     '撕': {'url': 'http://api.caonm.net/api/sit/s.php?qq=', 'liang': 0},
#     '加框': {'url': 'http://ovooa.caonm.net/API/head/?QQ=', 'liang': 0},
#     '小马赞': {'url': 'http://ovooa.caonm.net/API/zan/api.php?QQ=', 'liang': 0},
#     '丢': {'url': 'http://ovooa.caonm.net/API/diu/api.php?QQ=', 'liang': 0},
#     '遗照': {'url': 'http://lkaa.top/API/yi/?QQ=', 'liang': 0},
#     '猫猫赞': {'url': 'http://xiaobapi.top/api/xb/api/zan_2.php?qq=', 'liang': 0},
#     '彩遗': {'url': 'https://xiaobapi.top/api/xb/api/ji.php?qq=', 'liang': 0},
#     '牵': {'url': 'http://api.tangdouz.com/wz/qian.php?q=', 'liang': 1},
#     '背刺': {'url': 'https://xiaobapi.top/api/xb/api/tong.php?qq=', 'liang': 2},
#     '坏': {'url': 'http://api.tangdouz.com/wz/py.php?q=', 'liang': 0},
#     '鄙视': {'url': 'http://xiaobai.klizi.cn/API/ce/bishi.php?qq=', 'liang': 0},
#     '捶': {'url': 'http://xiaobai.klizi.cn/API/gif/hammer.php?qq=', 'liang': 0},
#     '报时': {'url': 'http://xiaobai.klizi.cn/API/ce/msg.php?qq=', 'liang': 0},
#     '忘了他': {'url': 'http://api.caonm.net/api/shoux/h.php?qq=', 'liang': 0},
#     '儿子': {'url': 'http://api.caonm.net/api/wrz/r.php?qq=', 'liang': 0},
#     '拒绝': {'url': 'http://api.caonm.net/api/wjj/j.php?qq=', 'liang': 0},
#     '原谅': {'url': 'http://api.caonm.net/api/lmz/l.php?qq=', 'liang': 0},
#     '我老婆': {'url': 'http://api.caonm.net/api/nmy/n.php?qq=', 'liang': 0},
#     '女儿': {'url': 'http://api.caonm.net/api/wnr/n.php?qq=', 'liang': 0},
#     '让你': {'url': 'http://api.caonm.net/api/bgz/g.php?qq=', 'liang': 0},
#     '广告牌': {'url': 'http://api.caonm.net/api/dal/l.php?qq=', 'liang': 0},
#     '耍帅': {'url': 'http://api.caonm.net/api/zhua/h.php?qq=', 'liang': 0},
#     '黑化': {'url': 'http://api.caonm.net/api/whh/h.php?qq=', 'liang': 0},
#     '脆弱': {'url': 'http://api.caonm.net/api/cuir/c.php?qq=', 'liang': 0},
#     '精神': {'url': 'http://xiaobapi.top/api/xb/api/bqb_12.php?qq=', 'liang': 0},
#     '寄': {'url': 'http://api.caonm.net/api/jim/j.php?qq=', 'liang': 0},
#     '坤投篮': {'url': 'http://api.caonm.net/api/kunk/k.php?qq=', 'liang': 0},
#     '处男': {'url': 'https://xiaobapi.top/api/xb/api/chunan.php?qq=', 'liang': 0},
#     '安妮亚': {'url': 'http://api.caonm.net/api/any/any.php?qq=', 'liang': 0},
#     '估价': {'url': 'http://api.caonm.net/api/qgj/index.php?qq=', 'liang': 0},
#     '宣誓': {'url': 'https://xiaobapi.top/api/xb/api/xuanshi.php?qq=', 'liang': 0},
#     '洗衣机': {'url': 'http://xiaobapi.top/api/xb/api/xiyiji.php?qq=', 'liang': 0},
#     '单身狗': {'url': 'http://xiaobapi.top/api/xb/api/single_idcard.php?qq=', 'liang': 0},
#     '心碎': {'url': 'http://api.caonm.net/api/xins/x.php?qq=', 'liang': 0},
#     '最帅': {'url': 'http://api.caonm.net/api/zuis/z.php?qq=', 'liang': 0},
#     '嫁我': {'url': 'http://api.caonm.net/api/qiuh/q.php?qq=', 'liang': 0},
#     '要这个': {'url': 'https://xiaobapi.top/api/xb/api/this.php?qq=', 'liang': 0},
#     '敲': {'url': 'https://xiaobapi.top/api/xb/api/qiao.php?qq=', 'liang': 0},
#     'okk': {'url': 'http://api.caonm.net/api/okk/k.php?qq=', 'liang': 0},
#     '鄙视2': {'url': 'https://xiaobapi.top/api/xb/api/bishi.php?qq=', 'liang': 0},
#     '勾引': {'url': 'http://api.caonm.net/api/gouy/g.php?qq=', 'liang': 0},
#     '笔芯': {'url': 'https://xiaobapi.top/api/xb/api/bixinxin.php?qq=', 'liang': 0},
#     '偷瞄': {'url': 'https://xiaobapi.top/api/xb/api/toumiao.php?qq=', 'liang': 0},
#     'jojo': {'url': 'http://xiaobapi.top/api/xb/api/jojo.php?qq=', 'liang': 2},
#     '比心': {'url': 'http://api.caonm.net/api/bix/b.php?qq=', 'liang': 0},
#     '跟我处对象': {'url': 'http://api.caonm.net/api/xie/x.php?qq=', 'liang': 0},
#     '圈钱跑路': {'url': 'http://api.caonm.net/api/pao/p.php?qq=', 'liang': 0},
#     '膜拜': {'url': 'http://ovooa.caonm.net/API/face_worship/?QQ=', 'liang': 0},
#     '摸': {'url': 'http://ovooa.caonm.net/API/face_petpet/?QQ=', 'liang': 0},
#     '幻想': {'url': 'http://api.caonm.net/api/x_3/x.php?qq=', 'liang': 0},
#     '吃掉': {'url': 'http://ovooa.caonm.net/API/face_bite/?QQ=', 'liang': 0},
#     '什么东西': {'url': 'http://api.caonm.net/api/peng/p.php?qq=', 'liang': 0},
#     '2吃': {'url': 'http://api.caonm.net/api/bgz/g.php?qq=', 'liang': 0},
#     '咀嚼': {'url': 'http://api.caonm.net/api/chi/e.php?qq=', 'liang': 0},
#     '来一下': {'url': 'http://api.caonm.net/api/pdl/c.php?qq=', 'liang': 0},
#     '看完干活': {'url': 'http://xiaobapi.top/api/xb/api/back_to_work.php?qq=', 'liang': 0},
#     '有害垃圾': {'url': 'http://xiaobapi.top/api/xb/api/youhailaji.php?qq=', 'liang': 0},
#     '平板': {'url': 'http://api.caonm.net/api/wyx/p2.php?qq=', 'liang': 0},
#     '玩游戏': {'url': 'http://api.caonm.net/api/wyx/p.php?qq=', 'liang': 0},
#     '拿着': {'url': 'http://api.caonm.net/api/kan/kan_3.php?qq=', 'liang': 0},
#     '2举': {'url': 'http://api.caonm.net/api/kan/kan_4.php?qq=', 'liang': 0},
#     '3举': {'url': 'http://api.caonm.net/api/kan/kan_5.php?qq=', 'liang': 0},
#     '叽': {'url': 'http://api.caonm.net/api/kan/kan_6.php?qq=', 'liang': 0},
#     '道歉': {'url': 'http://api.caonm.net/api/kan/kan_8.php?qq=', 'liang': 0},
#     '手机': {'url': 'http://api.caonm.net/api/kan/kan_9.php?qq=', 'liang': 0},
#     '4举': {'url': 'http://h.xiaocha.fun/api/ju.php?qq=', 'liang': 0},
#     '拿牌': {'url': 'http://api.caonm.net/api/kan/kan.php?qq=', 'liang': 0},
#     '举': {'url': 'http://xiaobapi.top/api/xb/api/ju.php?qq=', 'liang': 0},
#     '听音乐': {'url': 'http://xiaobapi.top/api/xb/api/listen_music.php?qq=', 'liang': 0},
#     '警察': {'url': 'http://api.caonm.net/api/jcz2/p.php?qq=', 'liang': 0},
#     '警官': {'url': 'http://api.caonm.net/api/jcz/index.php?qq=', 'liang': 0},
#     '嘴': {'url': 'http://api.caonm.net/api/jiujiu/jiujiu.php?qq=', 'liang': 0},
#     '舔': {'url': 'http://api.caonm.net/api/tn/t.php?qq=', 'liang': 0},
#     '遮脸': {'url': 'http://api.caonm.net/api/huanl/h.php?qq=', 'liang': 0},
#     '可达鸭': {'url': 'https://xiaobapi.top/api/xb/api/cover_face_2.php?qq=', 'liang': 0},
#     '疑问': {'url': 'http://api.caonm.net/api/mb/wh.php?qq=', 'liang': 0},
#     '上电视': {'url': 'http://api.caonm.net/api/kds/k.php?qq=', 'liang': 0},
#     '这像画吗': {'url': 'http://api.caonm.net/api/hua/h.php?qq=', 'liang': 0},
#     '垃圾': {'url': 'http://api.caonm.net/api/ljt/l.php?qq=', 'liang': 0},
#     '为什么艾特我': {'url': 'http://api.caonm.net/api/why/at.php?qq=', 'liang': 0},
#     '墙纸': {'url': 'http://api.caonm.net/api/bz/w.php?qq=', 'liang': 0},
#     '求婚': {'url': 'http://ovooa.caonm.net/API/face_propose/?QQ=', 'liang': 0},
#     '感动哭了': {'url': 'http://ovooa.caonm.net/API/face_touch/?QQ=', 'liang': 0},
#     '高质量': {'url': 'http://ovooa.caonm.net/API/face_gao/?QQ=', 'liang': 0},
#     '咸鱼': {'url': 'http://ovooa.caonm.net/API/face_yu/?QQ=', 'liang': 0},
#     '快逃': {'url': 'http://xiaobai.klizi.cn/API/gif/escape.php?qq=', 'liang': 0},
#     '要钱钱': {'url': 'http://api.caonm.net/api/wyqq/q.php?qq=', 'liang': 0},
#     '瑟瑟': {'url': 'https://xiaobai.klizi.cn/API/gif/erotic.php?qq=', 'liang': 0},
#     '随机证书': {'url': 'https://xiaobai.klizi.cn/API/ce/zs.php?qq=', 'liang': 0},
#     '滚出': {'url': 'http://api.caonm.net/api/gun/index.php?qq=', 'liang': 0},
#     '羡慕': {'url': 'http://api.wqwlkj.cn/wqwlapi/xianmu.php?qq=', 'liang': 0},
#     '摸狗狗': {'url': 'http://api.caonm.net/api/wus/w.php?qq=', 'liang': 0},
#     '网络公主': {'url': 'http://api.caonm.net/api/yyy/y.php?qq=', 'liang': 0},
#     '删库': {'url': 'http://h.xiaocha.fun/api/pao.php?qq=', 'liang': 0},
#     '看电视': {'url': 'http://h.xiaocha.fun/api/kan.php?qq=', 'liang': 0},
#     '美女抬': {'url': 'http://h.xiaocha.fun/api/tai.php?qq=', 'liang': 0},
#     '难办': {'url': 'http://h.xiaocha.fun/api/ban.php?qq=', 'liang': 0},
#     '女拿': {'url': 'http://h.xiaocha.fun/api/na.php?qq=', 'liang': 0},
#     '拍死你': {'url': 'http://h.xiaocha.fun/api/pai.php?qq=', 'liang': 0},
#     '快溜': {'url': 'http://h.xiaocha.fun/api/liu/liu.php?QQ=', 'liang': 0},
#     '怒': {'url': 'http://h.xiaocha.fun/api/nu/nu.php?QQ=', 'liang': 0},
#     '不想上学': {'url': 'http://h.xiaocha.fun/api/xue/xue.php?QQ=', 'liang': 0},
#     '露脸': {'url': 'http://h.xiaocha.fun/api/lou/lou.php?QQ=', 'liang': 0},
#     '滑稽捶': {'url': 'http://h.xiaocha.fun/api/chui/chui.php?QQ=', 'liang': 0},
#     '咬2': {'url': 'http://h.xiaocha.fun/api/yao/yao.php?QQ=', 'liang': 0},
#     '心碎2': {'url': 'http://h.xiaocha.fun/api/sui/sui.php?QQ=', 'liang': 0},
#     '乡下人': {'url': 'http://api.caonm.net/api/txmb/6.php?qq=', 'liang': 0},
#     '灵动岛': {'url': 'http://api.caonm.net/api/txmb/3.php?qq=', 'liang': 0},
#     '流汗': {'url': 'http://api.caonm.net/api/txmb/1.php?qq=', 'liang': 0},
#     '纱雾举牌': {'url': 'http://api.caonm.net/api/wus/w.php?qq=', 'liang': 0},
#     '整一个': {'url': 'http://apicaonm.net/api/zyg/gei.php?qq=', 'liang': 0},
#     '老干妈': {'url': 'http://api.caonm.net/api/lgm/index.php?qq=', 'liang': 0},
#     '拿手机': {'url': 'http://h.xiaocha.fun/api/sj.php?qq=', 'liang': 0},
#     '我的人': {'url': 'http://h.xiaocha.fun/api/wode.php?qq=', 'liang': 0},
#     '喝饮料': {'url': 'http://h.xiaocha.fun/api/xi.php?qq=', 'liang': 0},
#     '看淡了': {'url': 'http://h.xiaocha.fun/api/dan.php?qq=', 'liang': 0},
#     '坤证': {'url': 'http://api.caonm.net/api/txmb/7.php?qq=', 'liang': 0},
#     '懒羊羊': {'url': 'http://api.caonm.net/api/lyy/l.php?qq=', 'liang': 0},
#     '摇摆': {'url': 'http://api.caonm.net/api/ajl/y.php?qq=', 'liang': 0},
#     '颜色': {'url': 'http://api.caonm.net/api/sjbc/y.php?qq=', 'liang': 0},
#     '走路': {'url': 'http://api.caonm.net/api/zoul/y.php?qq=', 'liang': 0},
#     '女装协议': {'url': 'http://api.caonm.net/api/jqxy/n.php?qq=', 'liang': 0},
#     '进群协议': {'url': 'http://api.caonm.net/api/jqxy/j.php?qq=', 'liang': 0},
#     '拿来吧你': {'url': 'http://xiaobapi.top/api/xb/api/give_me_that.php?qq=', 'liang': 0},
#     '颜值高': {'url': 'http://xiaobapi.top/api/xb/api/error.php?qq=', 'liang': 0},
#     '亲亲': {'url': 'http://api.caonm.net/api/ddqq/y.php?qq=', 'liang': 0},
#     '按下': {'url': 'http://api.caonm.net/api/anniu/a.php?qq=', 'liang': 0},
#     '50': {'url': 'http://api.caonm.net/api/v50/b.php?qq=', 'liang': 0},
#     '涩图': {'url': 'http://api.caonm.net/api/mstl/s.php?qq=', 'liang': 0},
#     '杜蕾斯': {'url': 'http://api.caonm.net/api/byt/b.php?qq=', 'liang': 0},
#     '打篮球': {'url': 'http://www.xiaoqiandtianyi.tk/api/cxk.php?QQ=', 'liang': 0},
#     '挥拳': {'url': 'http://api.caonm.net/api/hq/chui.php?qq=', 'liang': 0},
#     '写代码': {'url': 'http://api.wqwlkj.cn/wqwlapi/jwxdm.php?qq=', 'liang': 0},
#     '安排': {'url': 'http://api.wqwlkj.cn/wqwlapi/anpai.php?qq=', 'liang': 0},
#     '萌新一个': {'url': 'http://api.wqwlkj.cn/wqwlapi/wsmx.php?qq=', 'liang': 0},
#     '差评': {'url': 'http://api.wqwlkj.cn/wqwlapi/cp.php?qq=', 'liang': 0},
#     '好评': {'url': 'http://api.wqwlkj.cn/wqwlapi/hp.php?qq=', 'liang': 0},
#     '坤举旗': {'url': 'http://api.wqwlkj.cn/wqwlapi/kunjuqi.php?qq=', 'liang': 0},
#     '开始摆烂': {'url': 'http://api.luanmo.top/API/tu_bailan?qq=', 'liang': 0},
#     '保护': {'url': 'http://api.luanmo.top/API/tu_dog2?qq=', 'liang': 0},
#     '地图头像': {'url': 'http://api.wqwlkj.cn/wqwlapi/zgdt.php?qq=', 'liang': 0},
#     '小c酱': {'url': 'http://api.caonm.net/api/xc/index.php?', 'liang': 0},
#     'mc酱': {'url': 'http://api.caonm.net/api/mc/index.php?', 'liang': 0},
#     '兽猫酱': {'url': 'http://api.caonm.net/api/smj/index.php?', 'liang': 0},
#     '柴郡': {'url': 'http://api.caonm.net/api/chai/c.php?', 'liang': 0},
#     'ikun': {'url': 'http://api.caonm.net/api/kun/k.php?', 'liang': 0},
#     '龙图': {'url': 'http://api.caonm.net/api/long/l.php?', 'liang': 0},
#     '变魔术': {'url': 'http://api.caonm.net/api/tax/y.php?qq=', 'liang': 0},
#     '结婚': {'url': 'https://api.caonm.net/api/jhzz/j.php?qq=', 'liang': 2},
#     '两只猫': {'url': 'https://api.caonm.net/api/xmmz/y.php?qq=', 'liang': 0},
#     '煮': {'url': 'https://api.caonm.net/api/huos/y.php?qq=', 'liang': 0},
#     '画画': {'url': 'https://api.caonm.net/api/huaa/h.php?qq=', 'liang': 0},
#     '打鸡蛋': {'url': 'https://api.caonm.net/api/chaof/y.php?qq=', 'liang': 0},
#     '2舔': {'url': 'https://api.caonm.net/api/chixg/y.php?qq=', 'liang': 0},
#     '枕头': {'url': 'https://api.caonm.net/api/zhent/y.php?qq=', 'liang': 0},
#     'IKUN': {'url': 'http://api.caonm.net/api/ikz/i.php?qq=', 'liang': 0},
#     '滚': {'url': 'http://api.caonm.net/api/gund/g.php?qq=', 'liang': 0},
#     '注意身份': {'url': 'http://api.caonm.net/api/zynsf/z.php?qq=', 'liang': 0},
#     '翻画板': {'url': 'http://api.caonm.net/api/dakai/a.php?qq=', 'liang': 0},
#     '街舞': {'url': 'https://api.caonm.net/api/tmcw/y.php?qq=', 'liang': 0},
#     '蹭': {'url': 'https://api.caonm.net/api/cence/y.php?qq=', 'liang': 0},
#     '2拍': {'url': 'https://api.caonm.net/api/paid/y.php?qq=', 'liang': 0},
#     '装高手': {'url': 'http://www.xiaoqiandtianyi.tk/api/z.php?qq=', 'liang': 0},
#     '追': {'url': 'https://api.caonm.net/api/zhuid/y.php?qq=', 'liang': 0},
#     '2敲': {'url': 'https://api.caonm.net/api/qiaod/y.php?qq=', 'liang': 0},
#     '上吊': {'url': 'https://api.caonm.net/api/shangd/y.php?qq=', 'liang': 0},
#     '跳舞': {'url': 'http://api.caonm.net/api/tiaow/y.php?qq=', 'liang': 0},
#     '诈尸': {'url': 'http://api.caonm.net/api/zhas/y.php?qq=', 'liang': 0},
#     '踢球': {'url': 'https://api.caonm.net/api/tiqiu/y.php?qq=', 'liang': 0},
#     '骗子': {'url': 'https://api.caonm.net/api/pianzi/c.php?qq=', 'liang': 0},
#     '导管': {'url': 'https://api.caonm.net/api/daoguan/c.php?qq=', 'liang': 0},
#     '强行瑟瑟': {'url': 'https://api.caonm.net/api/kapian/c.php?qq=', 'liang': 0},
#     '我牛子呢': {'url': 'https://api.caonm.net/api/kapian/c2.php?qq=', 'liang': 0},
#     '恶魔': {'url': 'https://api.caonm.net/api/kapian/c3.php?qq=', 'liang': 0},
#     '演员': {'url': 'https://api.caonm.net/api/madou/c2.php?qq=', 'liang': 0},
#     '狗呢': {'url': 'https://api.caonm.net/api/asc/c.php?qq=', 'liang': 0},
#     '不幸': {'url': 'https://api.caonm.net/api/asc/c2.php?qq=', 'liang': 0},
#     '老实点': {'url': 'https://api.caonm.net/api/asc/c3.php?qq=', 'liang': 0},
#     '动漫画画': {'url': 'https://api.caonm.net/api/asc/c4.php?qq=', 'liang': 0},
#     '木鱼': {'url': 'https://api.caonm.net/api/muyu/y.php?qq=', 'liang': 0},
#     '金钱攻击': {'url': 'https://api.caonm.net/api/jingq/y.php?qq=', 'liang': 0},
#     '安全感': {'url': 'http://api.caonm.net/api/anqg/c.php?qq=', 'liang': 0},
#     '陪睡券': {'url': 'https://api.caonm.net/api/asc/c5.php?qq=', 'liang': 0},
#     '男同': {'url': 'https://api.caonm.net/api/asc/c6.php?qq=', 'liang': 0},
#     '掀墙纸': {'url': 'https://api.andeer.top/API/gif_wallpaper.php?qq=', 'liang': 0},
#     '胡桃咬': {'url': 'https://api.andeer.top/API/gif_hutao_bite.php?qq=', 'liang': 0},
#     '可莉吃': {'url': 'https://api.andeer.top/API/gif_klee_eat.php?qq=', 'liang': 0},
#     '崇拜': {'url': 'https://api.andeer.top/API/gif_worship.php?qq=', 'liang': 0},
#     '嘎达': {'url': 'https://api.andeer.top/API/img_tr.php?qq=', 'liang': 0},
#     '要亲亲': {'url': 'https://api.andeer.top/API/img_kiss_1.php?qq=', 'liang': 0},
#     '宝可梦': {'url': 'https://api.andeer.top/API/img_pokemon.php?qq=', 'liang': 0},
#     '可爱': {'url': 'https://api.andeer.top/API/img_cute.php?qq=', 'liang': 0},
#     '蒙娜丽莎': {'url': 'https://api.andeer.top/API/img_mnls.php?qq=', 'liang': 0},
#     '精神涣散': {'url': 'https://api.andeer.top/API/no_attention.php?qq=', 'liang': 0},
#     '贴贴': {'url': 'https://api.andeer.top/API/img_kiss1.php?bqq=', 'liang': 3},
#     '击剑': {'url': 'https://api.andeer.top/API/gif_beat_j.php?bqq=', 'liang': 3},
#     '过来洗头': {'url': 'https://api.andeer.top/API/moca.php?bqq=', 'liang': 3},
#     '正在加载': {'url': 'https://api.andeer.top/API/img_loading.php?qq=', 'liang': 0},
#     '体操服': {'url': 'http://api.caonm.net/api/jupai/m.php?qq=', 'liang': 0},
#     '技能': {'url': 'http://api.caonm.net/api/jineng/y.php?qq=', 'liang': 0},
#     'GKD': {'url': 'http://api.caonm.net/api/kapian/c5.php?qq=', 'liang': 0},
#     '无法瑟瑟': {'url': 'http://api.caonm.net/api/kapian/c4.php?qq=', 'liang': 0},
#     '目录': {'url': 'http://api.caonm.net/api/asc/c9.php?qq=', 'liang': 0},
#     '床上一躺': {'url': 'http://api.caonm.net/api/asc/c8.php?qq=', 'liang': 0},
#     '啊！': {'url': 'http://api.caonm.net/api/asc/c7.php?qq=', 'liang': 0},
#     '包夜': {'url': 'http://api.caonm.net/api/guoy/g.php?qq=', 'liang': 0},
#     '报警了': {'url': 'http://api.caonm.net/api/baon/1.php?qq=', 'liang': 0},
#     '超市': {'url': 'http://api.caonm.net/api/chaop/j.php?qq=', 'liang': 2},
#     '星期四': {'url': 'http://api.caonm.net/api/kfc/50.php?qq=', 'liang': 0},
#     '女同': {'url': 'http://api.caonm.net/api/asc/c66.php?qq=', 'liang': 0},
#     '芙蓉王': {'url': 'http://api.caonm.net/api/yan/y.php?qq=', 'liang': 0},
#     '望远镜': {'url': 'https://api.caonm.net/api/wyj/w.php?qq=', 'liang': 0},
#     '完美': {'url': 'http://api.caonm.net/api/meiyou/c.php?qq=', 'liang': 0},
#     '汤姆猫': {'url': 'http://api.caonm.net/api/tmgx/y.php?qq=', 'liang': 0},
#     '一脚': {'url': 'http://api.caonm.net/api/zjyj/y.php?qq1=', 'liang': 2},
#     '大哭': {'url': 'http://api.caonm.net/api/txmb/8.php?qq=', 'liang': 0},
#     '情侣': {'url': 'http://api.caonm.net/api/mxbc/m.php?qq=', 'liang': 0},
#     '名片': {'url': 'http://api.caonm.net/api/tp/m.php?qq=', 'liang': 0},
#     '美女抱': {'url': 'http://api.caonm.net/api/jupai/d.php?qq=', 'liang': 0}
# }
#
#     print(html_to_png("emoticon", data))
