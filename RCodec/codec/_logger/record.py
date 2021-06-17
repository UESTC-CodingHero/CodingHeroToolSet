from ..common import Mode, PatKey


class Record(dict):
    """
    关于编码信息的一个记录，用于填充BD-rate表
    """
    # @formatter:off
    Container = list
    _data_type = {
        PatKey.Line_Bit             : (int, Container),
        PatKey.Line_Time            : (float, Container),
        PatKey.Line_Psnr_Y          : (float, Container),
        PatKey.Line_Psnr_U          : (float, Container),
        PatKey.Line_Psnr_V          : (float, Container),
        PatKey.Summary_Psnr_Y       : (float, None),
        PatKey.Summary_Psnr_U       : (float, None),
        PatKey.Summary_Psnr_V       : (float, None),
        PatKey.Summary_Bitrate      : (float, None),
        PatKey.Summary_Encode_Time  : (float, None),
        PatKey.Summary_Decode_Time  : (float, None)
    }
    DEFAULT = 0
    # @formatter:on

    def __init__(self, _id: int, mode: Mode, name: str):
        """
        初始化一个记录
        :param _id: 当前记录的序列的ID
        :param mode: 当前记录所属的编码模式
        :param name: 当前记录所属的序列简称
        """
        super().__init__()
        self.id = _id
        self.mode = mode
        self.name = name
        self.qp = Record.DEFAULT

    def __setitem__(self, key, value):
        data_type, container = Record._data_type[key]
        value = data_type(value)
        if container is None:
            super(Record, self).__setitem__(key, value)
        else:
            if not isinstance(value, type(container)):
                value = [value]
            values = (self.get(key) or container()) + container(value)
            super(Record, self).__setitem__(key, values)

    def __getitem__(self, key):
        return self.get(key) if self.get(key) else Record.DEFAULT

    def __str__(self):
        values = [self.name, str(self.qp)]
        for k in self.keys():
            values.append(str(self.__getitem__(k)))
        return ",".join(values)

    def __repr__(self):
        return self.__str__()
