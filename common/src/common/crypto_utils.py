import hashlib
from typing import Union


def md5_hash(data: Union[str, bytes]) -> str:
    """
    计算 MD5 哈希值
    
    Args:
        data: 字符串或字节数据
        
    Returns:
        MD5 哈希值（32位小写）
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    
    md5_obj = hashlib.md5()
    md5_obj.update(data)
    return md5_obj.hexdigest().lower()


def short_md5(data: Union[str, bytes], length: int = 16) -> str:
    """
    计算并截取 MD5 哈希值
    
    Args:
        data: 字符串或字节数据
        length: 截取长度（默认16位）
        
    Returns:
        截取后的 MD5 哈希值
    """
    return md5_hash(data)[:length]
