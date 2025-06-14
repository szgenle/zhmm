from typing import Any, Dict


def is_equal(dict1: Dict[Any, Any], dict2: Dict[Any, Any]) -> bool:
    """
    深度比较两个字典是否完全相同

    Args:
        dict1: 第一个字典
        dict2: 第二个字典

    Returns:
        bool: 如果两个字典完全相同返回True，否则返回False
    """
    # 类型检查
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return False

    # 键集合比较
    if set(dict1.keys()) != set(dict2.keys()):
        return False

    # 逐个比较值
    for key in dict1:
        val1 = dict1[key]
        val2 = dict2[key]

        # 如果值是字典，递归比较
        if isinstance(val1, dict) and isinstance(val2, dict):
            if not is_equal(val1, val2):
                return False
        # 其他情况直接比较
        elif val1 != val2:
            return False

    return True
