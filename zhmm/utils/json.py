def get_values_from_json(json_data, key_path):
    """
    从JSON数据中获取指定键路径的所有值。

    :param json_data: JSON数据（字典或列表）
    :param key_path: 键路径，例如 "as/b"
    :return: 指定键路径的所有值
    """
    keys = key_path.split('/')
    result = []

    def _find_values(data, current_keys):
        if not current_keys:
            return

        key = current_keys[0]
        if isinstance(data, dict):
            if key in data:
                if len(current_keys) == 1:
                    result.append(data[key])
                else:
                    _find_values(data[key], current_keys[1:])
        elif isinstance(data, list):
            for item in data:
                _find_values(item, current_keys)

    _find_values(json_data, keys)
    return result
