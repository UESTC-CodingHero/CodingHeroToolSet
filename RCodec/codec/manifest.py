# 以下几行导入的包不能删掉
import glob
import json
import os
from typing import Union, Dict, Optional

from ._runner.codec_runner import Codec
from .cfg import TEMPLATE_CONFIG
from .common import ParamType, PatKey, ConfigKey
from ._runner.codec_cfg import Encoder, Decoder, Merger


class SupportedCodec(object):
    _codecs: Dict[str, Codec] = dict()

    @staticmethod
    def _parse_cfg(global_cfg: str):
        global_cfg_dict = dict()
        if os.path.exists(global_cfg):
            with open(global_cfg, encoding="UTF-8") as fp:
                for line in fp:
                    if line.startswith("#") or len(line.strip()) == 0:
                        continue
                    else:
                        k_v = line.split("=")
                        if len(k_v) == 2:
                            try:
                                v = k_v[1].strip()
                                if len(v) == 0:
                                    v = None
                                else:
                                    special_chars = ['"', "'"]
                                    for sc in special_chars:
                                        if v.startswith(sc) and v.endswith(sc):
                                            v = v.strip(sc)
                                            # 不要重复strip
                                            break
                                global_cfg_dict[k_v[0].strip()] = v
                            except ValueError as _:
                                print(f"Ignore unknown key: '{k_v[0]}', "
                                      f"Valid keys are: {[e for e in ConfigKey.__dict__.values()]}")
        return global_cfg_dict

    @staticmethod
    def register_codec(codec: [Union[str, Codec]]):
        """
        将给定的编码器注册到系统

        :param codec: 编码器配置文件或编码器实例
        :return: True 如果注册成功，否则 False
        """
        if isinstance(codec, Codec):
            if SupportedCodec._codecs.get(codec.name) is None:
                SupportedCodec._codecs[codec.name] = codec
                setattr(SupportedCodec, codec.name, codec)
                ok = codec.encoder_cfg.pattern.get(PatKey.Summary_Psnr_Y) or \
                     codec.encoder_cfg.param_key.get(ParamType.Sequence)
                return ok is not None
        elif isinstance(codec, str) and os.path.exists(codec):
            with open(codec, encoding="UTF-8") as fp:
                lines = fp.readlines()
                for i, line in enumerate(lines):
                    line = line.strip()
                    if len(line) == 0 or line.startswith("import") or line.startswith("from") or line.startswith("#"):
                        continue
                    elif line.strip().startswith(Codec.__name__):
                        temp_var_name = "_temp"
                        exec(f"{temp_var_name} = {''.join(lines[i:])}")
                        return SupportedCodec.register_codec(locals().get(temp_var_name))
                    elif i == 0 and line.strip().startswith('{'):
                        fp.seek(0, os.SEEK_SET)
                        cfg = json.loads(fp.read())
                        encoder = cfg.get("encoder")
                        decoder = cfg.get("decoder")
                        merger = cfg.get("merger")
                        if merger is not None:
                            codec = Codec(encoder=Encoder(**encoder),
                                          decoder=Decoder(**decoder),
                                          merger=Merger(**merger))
                        else:
                            codec = Codec(encoder=Encoder(**encoder),
                                          decoder=Decoder(**decoder),
                                          merger=None)
                        return SupportedCodec.register_codec(codec)
        return False

    @staticmethod
    def _handle(path: str, handle_func: callable, filter_func: callable = None):
        if path and os.path.exists(path) and handle_func:
            if os.path.isdir(path):
                if filter_func:
                    files = filter_func(path)
                else:
                    files = os.listdir(path)
                return [handle_func(os.path.join(path, f)) for f in files]
            elif os.path.isfile(path):
                return handle_func(path)
        else:
            return None

    @staticmethod
    def init(global_cfg: Optional[str] = None):
        """
        从配置文件初始化codec, 全局变量等

        具体支持的配置参数请参考codec.common.ConfigKey

        :param global_cfg: 配置文件的路径
        :return: 如果初始化成功，返回 True，否则返回 False
        """
        if global_cfg is None:
            global_cfg = TEMPLATE_CONFIG
        cfg_dict = SupportedCodec._handle(global_cfg, SupportedCodec._parse_cfg, None)
        if cfg_dict and len(cfg_dict) > 0:
            if cfg_dict.get(ConfigKey.CFG_DIR):
                def filter_func(path):
                    pat = cfg_dict.get(ConfigKey.CFG_PAT)
                    if pat is None:
                        return os.listdir(path)
                    else:
                        result = []
                        for p in str(pat).split(","):
                            result += glob.glob(os.path.join(path, p))
                        return result

                SupportedCodec._handle(cfg_dict.get(ConfigKey.CFG_DIR), SupportedCodec.register_codec, filter_func)
            for k, v in cfg_dict.items():
                setattr(SupportedCodec, k, v)
            return True
        return False

    @staticmethod
    def find_by_name(name: str):
        for _codec_name, codec in SupportedCodec._codecs.items():
            if _codec_name == name:
                return codec
        return None

    @staticmethod
    def dump():
        keys = [
            ConfigKey.CFG_DIR,
            ConfigKey.CFG_PAT,
            ConfigKey.TMP_DIR,
            ConfigKey.BIN_DIR,
            ConfigKey.REC_DIR,
            ConfigKey.DEC_DIR,
            ConfigKey.STDOUT_DIR,
            ConfigKey.STDERR_DIR,
            ConfigKey.PREFIX_ENCODE,
            ConfigKey.PREFIX_DECODE,
            ConfigKey.SUFFIX_STDOUT,
            ConfigKey.SUFFIX_STDERR,
        ]
        for key in keys:
            v = SupportedCodec.__getattribute__(SupportedCodec, key)
            print(key, ":", v)
        print("Supported Codecs: ", end="[")
        for name, codec in SupportedCodec._codecs.items():
            print(name, end=", ")
        print("]")
