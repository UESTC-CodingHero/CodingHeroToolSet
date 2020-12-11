import os
import sys
import time
import hashlib


def get_hash(max_len=4, seed=None):
    """
    获取HASHCODE
    :param max_len: 返回hashcode的前N位
    :param seed: 如果未设置(为None或者空字符串或者空列表)，则使用系统时间作为 待hash字符串
    如果设置了，先判断是否为文件，如果为文件，则计算该文件的hash值，否则将其看作字符串，计算该字符串的hash值
    :return:
    """
    _md5 = hashlib.md5()
    if seed is None or (isinstance(seed, list) or isinstance(seed, str)) and len(seed) == 0:
        seed = time.time()
    if (isinstance(seed, list) and len(seed) == 1 and os.path.exists(seed[0]) or
            isinstance(seed, str) and os.path.exists(seed)):
        file = seed[0]
        with open(file, 'rb') as f:
            _md5.update(f.read())
    else:
        _md5.update(str(seed).encode("utf-8"))
    hashcode = str(_md5.hexdigest())
    hash_len = len(hashcode)
    max_len = max_len if max_len <= hash_len else hash_len
    return hashcode[0:max_len].upper()


if __name__ == '__main__':
    print(get_hash(seed=sys.argv[1:]))
