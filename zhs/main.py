import os
import sys
import json
import argparse
import platform
from functools import partial
from contextlib import suppress
from fucker import Fucker
from logger import logger
from ObjDict import ObjDict
from utils import showImage, cookie_jar_to_list
from utils import getConfigPath, getRealPath, versionCmp

DEFAULT_CONFIG = {
    "username": "",
    "password": "",
    "qrlogin": True,
    "save_cookies": True,
    "proxies": {},
    "logLevel": "INFO",
    "tree_view": True,
    "progressbar_view": True,
    "qr_extra": {
        "show_in_terminal": None,
        "ensure_unicode": False
    },
    "image_path":"",
    "pushplus": {
        "enable": False,
        "token": ""
    },
    "bark":{
        "enable": False,
        "token": "https://example.com/xxxxxxxxx"
    },
    "config_version": "1.4.0",
    "ai": {
        "enabled": True,
        "use_zhidao_ai": True,
        "openai": {
            "api_base": "https://api.openai.com",
            "api_key": "sk-",
            "model_name": "claude-3-5-sonnet-20240620"
        },
        "ppt_processing": {
            "provide_to_ai": False,
            "moonShot": {
                "base_url": "https://api.moonshot.cn/v1",
                "api_key": "sk-",
                "delete_after_convert": True
            }
        },
        "use_stream": True
    }
}
# get config or create one if not exist
CONFIG_PATH = os.environ.get("FUCKCOURSE_CONFIG", getConfigPath())
ROOT_CONFIG = CONFIG_PATH != getConfigPath()

def _read_zhs_config():
    if not os.path.isfile(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="UTF-8") as f:
        root = json.load(f)
    if ROOT_CONFIG:
        return root.get("zhs", {})
    return root

def _write_zhs_config(data):
    if ROOT_CONFIG:
        root = {}
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="UTF-8") as f:
                root = json.load(f)
        root["zhs"] = data
    else:
        root = data
    with open(CONFIG_PATH, "w", encoding="UTF-8") as f:
        json.dump(root, f, indent=4, ensure_ascii=False)

section = _read_zhs_config()
if section:
    config = ObjDict(section, default=None)
    if "config_version" not in config:
        config.config_version = "1.0.0"
    if versionCmp(config.config_version, DEFAULT_CONFIG["config_version"]) < 0:
        new = ObjDict(DEFAULT_CONFIG, default=None)
        if versionCmp(config.config_version, "1.0.1") < 0:
            config.pop("qr_extra", None)
        if versionCmp(config.config_version, "1.3.0") < 0:
            pushplus = config.pop("push", {})
            new.pushplus.update(pushplus)
        config.pop("config_version", None)
        new.update(config)
        config = new
        _write_zhs_config(dict(config))
        print("****Config file updated****")
else:
    config = ObjDict(DEFAULT_CONFIG, default=None)
    _write_zhs_config(dict(config))

# parse arguments
parser = argparse.ArgumentParser(prog="ZHS Fucker")
parser.add_argument("-c", "--course", type=str, nargs="+",
                    help="CourseId or recruitAndCourseId, can be found in URL")
parser.add_argument("-v", "--videos", type=str, nargs="+",
                    help="Video IDs(fileId in URL, or, videoId found in API response")
parser.add_argument("-u", "--username", type=str,
                    help="if not set anywhere, will be prompted")
parser.add_argument("-p", "--password", type=str,
                    help="If not set anywhere, will be prompted. Be careful, it will be stored in history")
parser.add_argument("-s", "--speed", type=float,
                    help="Video Play Speed, default value is maximum speed found on site")
parser.add_argument("-t", "--threshold", type=float,
                    help="Video End Threshold, above this will be considered finished, overloaded when there are questions left unanswered")
parser.add_argument("-l", "--limit", type=int, default=0,
                    help="Time Limit (in minutes, 0 for no limit), default is 0")
parser.add_argument("-q", "--qrlogin", action="store_true",
                    help="Use QR Login")
parser.add_argument("-d", "--debug", action="store_true", help="Debug Mode")
parser.add_argument("--show_in_terminal",
                    action="store_true", help="Show QR in terminal")
parser.add_argument("--proxy", type=str,
                    help="Proxy Config, e.g: http://127.0.0.1:8080")
parser.add_argument("--tree_view", type=bool,
                    help="print the tree progress view of the course")
parser.add_argument("--progressbar_view", type=bool,
                    help="print the progressbar view of the course")
parser.add_argument("--image_path", type=str,
                    help="Image save path, default is empty (do not save)")
args = parser.parse_args()

course = args.course
username = args.username or config.username
password = args.password or config.password
qrlogin = args.qrlogin or config.qrlogin or True  # Force enabled for v2.3.*
save_cookies = config.save_cookies or False
qr_extra = config.qr_extra or ObjDict(default=None)
show_in_terminal = args.show_in_terminal or config.qr_extra.show_in_terminal
tree_view = args.tree_view or config.tree_view
progressbar_view = args.progressbar_view or config.progressbar_view
image_path = args.image_path or config.image_path
if show_in_terminal is None:
    # Defaults to terminal in Windows
    show_in_terminal = platform.system() == "Windows"
ensure_unicode = qr_extra.ensure_unicode or False
logger.setLevel("DEBUG" if args.debug else (config.logLevel or "WARNING"))
proxies = config.proxies or {}
pushplus_token = config.pushplus.enable and config.pushplus.token or ""
bark_token = config.bark.enable and config.bark.token or ""

if logger.getLevel() == "DEBUG":
    print("*****************************\n" +
          "DEBUG MODE ENABLED\n" +
          "SENSITIVE DATA WILL BE LOGGED\n" +
          "*****************************\n")

if args.proxy:  # parse proxy
    match args.proxy.lower().split("://"):
        case ["http" | "https", proxy]:
            proxies["http"] = args.proxy
            proxies["https"] = args.proxy
        case ["socks5", proxy]:
            proxies["socks5"] = args.proxy
        case ["all", proxy]:
            proxies["http"] = args.proxy
            proxies["https"] = args.proxy
            proxies["socks5"] = args.proxy
        case [schema]:
            print(f"*Unsupported proxy type: {schema}")
            exit(1)

# create an instance, now we are talking... or fucking
fucker = Fucker(proxies=proxies, speed=args.speed, end_thre=args.threshold, limit=args.limit,
                pushplus_token=pushplus_token, bark_token=bark_token, tree_view=tree_view, progressbar_view=progressbar_view, image_path=image_path)

cookies_path = os.environ.get("FUCKCOURSE_COOKIES", getRealPath("./cookies.json"))
ROOT_COOKIES = cookies_path != getRealPath("./cookies.json")

def _read_zhs_cookies():
    if not os.path.exists(cookies_path):
        return None
    with open(cookies_path, 'r', encoding="utf-8") as f:
        raw = f.read().strip()
    if not raw:
        return None
    root = json.loads(raw)
    if ROOT_COOKIES:
        return root.get("zhs")
    return root

def _save_zhs_cookies(cookies_data):
    root = {}
    if os.path.exists(cookies_path):
        with open(cookies_path, 'r', encoding="utf-8") as f:
            try:
                root = json.load(f)
            except json.JSONDecodeError:
                pass
    if ROOT_COOKIES:
        root["zhs"] = cookies_data
    else:
        root = cookies_data
    with open(cookies_path, 'w', encoding="utf-8") as f:
        json.dump(root, f, indent=2, ensure_ascii=False)

cookies_loaded = False
if save_cookies:
    cookies = _read_zhs_cookies()
    if cookies:
        with suppress(Exception):
            fucker.cookies = cookies
            ls = fucker.getZhidaoList()
            if ls:
                fucker.getZhidaoContext(ls[-1].secret)
            ls = fucker.getHikeList()
            if ls:
                fucker.getHikeContext(ls[-1].courseId)

            ls = fucker.getZhidaoAiList()  # 验证 session 对 AI 课程有效
            if ls:
                pass
            print("Successfully recovered from saved cookies\n")
            cookies_loaded = True


# first you need to login to get cookies
if not cookies_loaded:
    try:
        if qrlogin:
            callback = partial(
                showImage, show_in_terminal=show_in_terminal, ensure_unicode=ensure_unicode)
            fucker.login(use_qr=True, qr_callback=callback)
        else:
            fucker.login(username, password)
        print("Login Successful\n")
        if save_cookies:
            _save_zhs_cookies(cookie_jar_to_list(fucker.cookies))
    except Exception as e:
        print(e)
        exit(1)

# you can add cookies manually by setting cookies property of a Fucker instance
# notice that cookies of zhihuishu.com expires if you login again in somewhere else
# fucker.cookies = {}

# ── AI 配置验证（模块级，复用） ────────────────────────────────────────

def _validate_ai_config(ai_config):
    if not ai_config:
        raise ValueError("AI 配置未找到")
    if not isinstance(ai_config, dict):
        raise ValueError(f"AI 配置不是字典，而是 {type(ai_config)}")
    if ai_config.get("enabled") and ai_config.get("use_zhidao_ai"):
        _validate_openai_config(ai_config.get("openai", {}))
    _validate_ppt_config(ai_config.get("ppt_processing", {}))


def _validate_openai_config(openai_config):
    if not isinstance(openai_config, dict):
        raise ValueError(f"OpenAI 配置不是字典，而是 {type(openai_config)}")
    missing = [f for f in ["api_key", "api_base", "model_name"]
               if not openai_config.get(f)]
    if missing:
        raise ValueError(f"OpenAI 配置不完整，缺少: {', '.join(missing)}")


def _validate_ppt_config(ppt_config):
    if not isinstance(ppt_config, dict):
        raise ValueError(f"PPT 配置不是字典，而是 {type(ppt_config)}")
    if ppt_config.get("provide_to_ai"):
        moon = ppt_config.get("moonShot", {})
        missing = [f for f in ["base_url", "api_key"] if not moon.get(f)]
        if missing:
            raise ValueError(f"PPT 配置不完整，缺少: {', '.join(missing)}")


# ── 交互式课程选择 ──────────────────────────────────────────────

def _interactive_select_courses(fucker, ai_config):
    """交互式课程选择 — 获取所有课程列表，编号展示，用户多选"""
    print("正在获取课程列表...")

    entries = []

    # 知到课程
    try:
        for c in fucker.getZhidaoList():
            entries.append({"name": c.courseName, "id": c.secret, "type": "zhidao"})
    except Exception as e:
        print(f"  获取知到课程失败: {e}")

    # 共享课
    try:
        for c in fucker.getHikeList():
            entries.append({"name": c.courseName, "id": str(c.courseId), "type": "hike"})
    except Exception as e:
        print(f"  获取共享课失败: {e}")

    # AI 课程（仅在启用时）
    if ai_config:
        try:
            for c in fucker.getZhidaoAiList():
                entries.append({
                    "name": c.courseName, "id": str(c.courseId),
                    "type": "ai", "classId": str(c.classId)
                })
        except Exception as e:
            print(f"  获取 AI 课程失败: {e}")

    if not entries:
        print("未找到任何课程！请确认已选课。")
        return [], ai_config

    # 展示菜单
    type_labels = {"zhidao": "[知到]", "hike": "[共享课]", "ai": "[AI课]"}
    print(f"\n{'=' * 50}")
    print(f"共 {len(entries)} 门课程：")
    print(f"{'=' * 50}")
    for i, e in enumerate(entries):
        label = type_labels.get(e["type"], "")
        print(f"  [{i + 1:>2d}] {label} {e['name']}")
    print(f"  [a] 全部刷取")
    print(f"  [q] 退出")

    choice = input(f"\n请选择课程（多个用逗号分隔）: ").strip()

    if choice.lower() == "a":
        return entries, ai_config
    if choice.lower() == "q":
        print("已退出")
        sys.exit(0)

    selected = []
    for part in choice.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            idx = int(part) - 1
            if 0 <= idx < len(entries):
                selected.append(entries[idx])
            else:
                print(f"  无效编号: {part}")
        except ValueError:
            print(f"  无效输入: {part}")

    return selected, ai_config


# AI 配置验证（验证一次，失败只警告不阻塞普通课程）
ai_config = config.ai if config.ai and config.ai.get("enabled") else None
if ai_config:
    try:
        _validate_ai_config(ai_config)
    except ValueError as e:
        print(f"警告: AI 配置无效，跳过 AI 课程: {e}")
        ai_config = None

# 交互式课程选择（无 --course 时）
if not course:
    selected_entries, ai_config = _interactive_select_courses(fucker, ai_config)
    if not selected_entries:
        print("未选择任何课程，退出。")
        exit(1)

    for entry in selected_entries:
        entry_type = entry["type"]
        entry_id = entry["id"]
        try:
            if entry_type == "ai":
                fucker.fuckAiCourse(
                    int(entry_id), int(entry["classId"]), aiConfig=ai_config)
            elif entry_type == "zhidao":
                fucker.fuckZhidaoCourse(entry_id)
            else:  # hike
                fucker.fuckHikeCourse(entry_id)
        except Exception as e:
            logger.exception(e)
            print(f"  课程 {entry.get('name', entry_id)} 出错: {e}")
    exit(0)

# 指定了课程 → 逐个处理（支持 --course 和 --videos）
for c in course.copy():
    if args.videos:
        for v in args.videos:
            try:
                fucker.fuckVideo(course_id=c, video_id=v)
                print(f"fucked {v}")
                args.videos.remove(v)
            except Exception:
                pass
    else:
        try:
            fucker.fuckCourse(course_id=c)
            course.remove(c)
        except Exception as e:
            logger.exception(e)
            print(f"Error when fucking course {c}:\n{e}")
if args.videos:
    print(f"*the following videos are not fucked: {args.videos}")

# use fuckCourse method to fuck the entire course
# fucker.fuckCourse(course_id="")

# or if you want to fuck a video, use fuckVideo method
# fucker.fuckVideo(course_id="", file_id="")

# check the source code or README to find more info
