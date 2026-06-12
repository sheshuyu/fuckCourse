"""雨课堂 (yuketang) 微信扫码登录模块
"""

import io
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageOps


# ── 日志 ─────────────────────────────────────────────────────────────

LOG_DIR = os.environ.get("FUCKCOURSE_LOG_DIR", "")
LOG_FILE = os.path.join(LOG_DIR, "yuketang.log") if LOG_DIR else ""
_handlers = []
if LOG_FILE:
    _handlers.append(logging.FileHandler(LOG_FILE, encoding="utf-8"))
_handlers.append(logging.StreamHandler())
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=_handlers,
)


# ── 终端 QR 码渲染（移植自 zhs/utils.py） ──────────────────────────


def _show_image(img_bytes, show_in_terminal=True):
    if show_in_terminal:
        _terminal_qr_tty(img_bytes)


def _terminal_qr_tty(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    qr = img.resize((47, 47), Image.Resampling.NEAREST)
    qr = ImageOps.grayscale(qr)
    white = "\033[0;37;47m  "
    black = "\033[0;37;40m  "
    new_line = "\033[0m\n"
    col, row = qr.size
    qr_str = white * 49 + new_line
    for i in range(row):
        qr_str += white
        for j in range(col):
            qr_str += white if qr.getpixel((j, i)) > 128 else black
        qr_str += white + new_line
    qr_str += white * 49 + new_line
    print(qr_str)


BASE_URL = "https://changjiang.yuketang.cn"
CONFIG_FILE = "yuketang_config.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ── config ──────────────────────────────────────────────────────────


def _config_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / CONFIG_FILE
    return Path(__file__).parent / CONFIG_FILE


def _shared_cookies_path():
    return os.environ.get("FUCKCOURSE_COOKIES", "")


def _shared_config_path():
    return os.environ.get("FUCKCOURSE_CONFIG", "")


def _read_shared_json(filepath):
    try:
        if filepath and os.path.isfile(filepath):
            return json.loads(Path(filepath).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _write_shared_json(filepath, data):
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    Path(filepath).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_config():
    """读取配置：优先共享 cookies.json/config.json，回退本地 yuketang_config.json"""
    cookies_path = _shared_cookies_path()
    config_path = _shared_config_path()

    if cookies_path or config_path:
        result = {}
        if cookies_path:
            root = _read_shared_json(cookies_path)
            cookies = root.get("yuketang", "")
            if cookies:
                result["cookies"] = cookies
        if config_path:
            root = _read_shared_json(config_path)
            section = root.get("yuketang", {})
            uni_id = section.get("university_id", "")
            if uni_id:
                result["university_id"] = uni_id
        if result:
            return result

    # 回退本地
    path = _config_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_config(cookie_str=None, university_id=None, classroom_ids=None):
    """部分更新配置，优先共享文件，回退本地"""
    cookies_path = _shared_cookies_path()
    config_path = _shared_config_path()

    if cookies_path or config_path:
        if cookie_str is not None and cookies_path:
            root = _read_shared_json(cookies_path)
            root["yuketang"] = cookie_str
            _write_shared_json(cookies_path, root)
            logging.info("cookies 已保存到 %s", cookies_path)
        if university_id is not None and config_path:
            root = _read_shared_json(config_path)
            if "yuketang" not in root:
                root["yuketang"] = {}
            root["yuketang"]["university_id"] = str(university_id)
            _write_shared_json(config_path, root)
            logging.info("university_id 已保存到 %s", config_path)
        return

    # 回退本地
    config = load_config() or {}
    if cookie_str is not None:
        config["cookies"] = cookie_str
    if university_id is not None:
        config["university_id"] = str(university_id)
    if classroom_ids is not None:
        config["classroom_ids"] = classroom_ids
    _config_path().write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── cookie helpers ──────────────────────────────────────────────────


def parse_cookie_string(cookie_str):
    """把浏览器 cookie 字符串解析为 dict"""
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies


def cookie_dict_to_string(cookie_dict):
    """把 cookie dict 转回字符串"""
    return "; ".join(f"{k}={v}" for k, v in cookie_dict.items())


# ── validation ─────────────────────────────────────────────────────


def validate_cookies(cookie_str):
    """用 /v2/api/web/userinfo 验证 cookies 是否有效"""
    session = _make_session()
    session.cookies.update(parse_cookie_string(cookie_str))
    try:
        r = session.get(f"{BASE_URL}/v2/api/web/userinfo", timeout=15)
        if r.status_code == 200 and r.json().get("errcode") == 0:
            return True
    except Exception:
        pass
    logging.info("cookies 已失效")
    return False


# ── classroom list ──────────────────────────────────────────────────


def fetch_classroom_list(cookie_str):
    """用有效 cookies 获取用户课堂列表，返回 [{id, name, course_name, university_id}]"""
    session = _make_session()
    session.cookies.update(parse_cookie_string(cookie_str))
    classrooms = []
    try:
        r = session.get(f"{BASE_URL}/v2/api/web/courses/list", params={"identity": 2}, timeout=15)
        data = r.json()
        if data.get("errcode") != 0:
            return classrooms
        for c in data["data"].get("list", []):
            course = c.get("course", {})
            classrooms.append({
                "id": str(c.get("classroom_id", "")),
                "name": c.get("name", ""),
                "course_name": course.get("name", ""),
                "university_id": str(course.get("university_id", "")),
            })
    except Exception as e:
        print(f"  获取课堂列表失败: {e}")
    return classrooms


# ── QR login ────────────────────────────────────────────────────────


def _make_session():
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Referer": f"{BASE_URL}/authorize/wx-qrlogin",
            "X-Client": "web",
            "Xt-Agent": "web",
            "xtbz": "ykt",
        }
    )
    return s


def _get_qr_info(session):
    """调用 pre-info 获取 QR 信息，返回 {qrContent, qrImage, token} 或 None"""
    try:
        r = session.get(f"{BASE_URL}/api/v3/user/login/pre-info", timeout=15)
        data = r.json()
        if data.get("code") == 0:
            return data["data"]
        print(f"  [错误] 获取二维码失败: {data}")
    except Exception as e:
        print(f"  [错误] 获取二维码异常: {e}")
    return None


def _download_qr(session, qr_image_url):
    """下载 QR 码 PNG 图片，返回 bytes 或 None"""
    try:
        r = session.get(qr_image_url, timeout=30)
        if r.status_code == 200:
            return r.content
        print(f"  [错误] 下载二维码失败 HTTP {r.status_code}")
    except Exception as e:
        print(f"  [错误] 下载二维码异常: {e}")
    return None


def _display_qr(img_bytes):
    """终端内显示 QR 码"""
    _show_image(img_bytes)


def _fetch_university_id(session):
    """登录后从课程列表 API 提取 university_id"""
    try:
        r = session.get(
            f"{BASE_URL}/v2/api/web/courses/list",
            params={"identity": 2},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            courses = data.get("data", {}).get("list", [])
            for c in courses:
                uni_id = c.get("course", {}).get("university_id", 0)
                if uni_id:
                    return str(uni_id)
    except Exception:
        pass
    return ""


def _poll_login(session, token, timeout=120):
    """轮询 POST /api/v3/user/login 直到登录成功或超时

    返回 (cookie_string, university_id) 或 (None, None)
    """
    UNSCANNED_CODES = {50001}  # 未扫码 / 轮询中

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = session.post(
                f"{BASE_URL}/api/v3/user/login",
                json={"token": token},
                timeout=15,
            )
            data = r.json()
            code = data.get("code")
            msg = data.get("msg", "")

            if code == 0:
                cookies = session.cookies.get_dict()
                if not cookies:
                    continue
                uni_id = cookies.get("university_id", "")
                if not uni_id:
                    uni_id = _fetch_university_id(session)
                    cookies = session.cookies.get_dict()
                return cookie_dict_to_string(cookies), str(uni_id)

            if code in UNSCANNED_CODES:
                pass
            elif "EXPIRED" in msg.upper() or "过期" in msg:
                print("  二维码已过期，正在刷新...")
                return None, None
            else:
                if msg:
                    print(f"  [{msg}]")
        except Exception as e:
            print(f"  [警告] 轮询异常: {e}")

        time.sleep(2)

    print("  登录超时")
    return None, None


def qr_login():
    """完整扫码登录流程。返回 (cookie_string, university_id) 或退出。"""
    session = _make_session()
    print("\n启动微信扫码登录...")
    logging.info("启动微信扫码登录")

    for attempt in range(1, 6):
        if attempt > 1:
            print(f"\n第 {attempt} 次尝试...")

        qr_info = _get_qr_info(session)
        if not qr_info:
            time.sleep(2)
            continue

        img_bytes = _download_qr(session, qr_info["qrImage"])
        if not img_bytes:
            time.sleep(2)
            continue

        _display_qr(img_bytes)
        print("  等待扫码...")

        cookies, uni_id = _poll_login(session, qr_info["token"])
        if cookies:
            print(f"  登录成功！university_id = {uni_id}")
            logging.info("扫码登录成功, university_id=%s", uni_id)
            save_config(cookie_str=cookies, university_id=uni_id)
            return cookies, uni_id

    logging.error("扫码登录失败：重试次数用尽")
    print("登录失败：重试次数用尽")
    raise SystemExit(1)
