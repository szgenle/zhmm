from datetime import date, datetime


def today_str():
    return date.today().strftime("%Y-%m-%d")


def filename():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S').replace(':', '')