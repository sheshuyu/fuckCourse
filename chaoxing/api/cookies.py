# -*- coding: utf-8 -*-
import json
import os.path

import requests

from api.config import GlobalConst as gc


def _read_root_cookies():
    if not os.path.exists(gc.COOKIES_PATH):
        return {}
    with open(gc.COOKIES_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def _write_root_cookies(data):
    with open(gc.COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_cookies(session: requests.Session):
    data = _read_root_cookies()
    data["chaoxing"] = {k: v for k, v in session.cookies.items()}
    _write_root_cookies(data)


def use_cookies() -> dict:
    data = _read_root_cookies()
    if "chaoxing" in data:
        return data["chaoxing"]

    # 兼容旧的 cookies.txt 文本格式
    old_path = "cookies.txt"
    if os.path.exists(old_path):
        cookies = {}
        with open(old_path, "r") as f:
            buffer = f.read().strip()
            for item in buffer.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookies[k.strip()] = v.strip()
        return cookies

    return {}
