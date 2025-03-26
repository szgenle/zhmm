def truncate(s, max_length=32):
    """截断过长的字符串，并在尾部显示..."""
    if len(s) > max_length:
        return s[:max_length] + '...'
    return s
