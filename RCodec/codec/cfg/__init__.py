import os
from codec.common import ConfigKey

__author__ = "Xueli Cheng"

TEMPLATE_CONFIG = os.path.join(os.path.dirname(__file__), "global_config.properties")
with open(TEMPLATE_CONFIG, "w+", encoding="UTF-8") as file:
    def write(text):
        file.write(text)
        file.write("\n")


    write(f"# 该文件自动生成")
    write(f"# 编码器配置文件目录，用于实例化Codec对象")
    write(f"{ConfigKey.CFG_DIR} = {os.path.dirname(__file__)}")
    write(f"{ConfigKey.CFG_PAT} = *.py,*.json")
    write(f"{ConfigKey.TMP_DIR} = E:/tempYUV")
    write(f"{ConfigKey.BIN_DIR} = bin")
    write(f"{ConfigKey.REC_DIR} = rec")
    write(f"{ConfigKey.DEC_DIR} = dec")
    write(f"{ConfigKey.STDOUT_DIR} = stdout")
    write(f"{ConfigKey.STDERR_DIR} = stderr")
    write(f"{ConfigKey.PREFIX_ENCODE} = encode")
    write(f"{ConfigKey.PREFIX_DECODE} = decode")
    write(f"{ConfigKey.SUFFIX_STDOUT} = out")
    write(f"{ConfigKey.SUFFIX_STDERR} = err")
