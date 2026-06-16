#!/usr/bin/env python3
"""
长江雨课堂 PPT 批量下载脚本（多课堂版 · 支持微信扫码登录）

安装依赖:
    pip install requests Pillow

使用方法:
    python download_ppt.py                → 自动登录，从配置/API 获取课堂列表
    python download_ppt.py 12345678       → 下载指定课堂（逗号分隔多个 ID）
"""

import os
import sys
import time
import io
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image

# ── 自动扫码登录 ────────────────────────────────────────────────────
from yuketang_login import (
    load_config, save_config, validate_cookies, qr_login,
    fetch_classroom_list, USER_AGENT,
)

_here = Path(__file__).parent


def _ensure_login():
    """确保有有效的 cookies：先读 JSON 配置，失效则自动弹 QR 码登录"""
    config = load_config()
    if config:
        cookies = config.get("cookies", "")
        uni_id = config.get("university_id", "")
        if not cookies:
            cookies = config.get("COOKIE_STRING", "")
        if not uni_id:
            uni_id = config.get("UNIVERSITY_ID", "")
        if cookies and validate_cookies(cookies):
            # university_id 可能为空或 0，尝试从课程列表补充
            if not uni_id or uni_id == "0":
                courses = fetch_classroom_list(cookies)
                for c in courses:
                    uid = c.get("university_id", "")
                    if uid and uid != "0":
                        uni_id = uid
                        save_config(university_id=uni_id)
                        break
            return cookies, str(uni_id)
        print("Cookies 已失效或不存在，启动扫码登录...")
    else:
        print("未找到配置文件，启动扫码登录...")

    cookies, uni_id = qr_login()
    print()
    return cookies, uni_id


def _interactive_select(items, label_fn=str, select_all_label="全部下载",
                         prompt="选择"):
    """交互式多选菜单，返回选中的 items 子集

    Args:
        items: 选项列表
        label_fn: 每个选项的显示标签生成函数
        select_all_label: "全选"选项的显示文字
        prompt: 输入提示文字
    Returns:
        选中的 items 列表（'a' 全选返回全部；'q' 直接退出）
    """
    print(f"\n共 {len(items)} 项：")
    for i, item in enumerate(items):
        print(f"  [{i + 1}] {label_fn(item)}")

    print(f"  [a] {select_all_label}")
    print("  [q] 退出")
    choice = input(f"\n{prompt}（多个用逗号分隔）: ").strip()

    if choice.lower() == "a":
        return items
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
            if 0 <= idx < len(items):
                selected.append(items[idx])
            else:
                print(f"  无效编号: {part}")
        except ValueError:
            print(f"  无效输入: {part}")
    return selected


def _resolve_classroom_ids():
    """确定要下载的课堂 ID 列表

    优先级：命令行 > config.json > API 获取让用户选
    """
    # 1. 命令行参数
    if len(sys.argv) > 1:
        return [cid.strip() for cid in sys.argv[1].split(",") if cid.strip()]

    # 2. 配置文件
    config = load_config()
    if config:
        ids = config.get("classroom_ids", [])
        if ids:
            return [str(i) for i in ids]

    # 3. 从 API 获取课堂列表，让用户选
    print("正在获取课堂列表...")
    courses = fetch_classroom_list(COOKIE_STRING)
    if not courses:
        print("未找到任何课堂，请确认已选课。")
        raw = input("请输入课堂 ID（多个用逗号分隔）: ").strip()
        return [cid.strip() for cid in raw.split(",") if cid.strip()]

    selected = _interactive_select(
        courses,
        label_fn=lambda c: f"{c.get('course_name') or c.get('name') or c['id']}  (id={c['id']})",
    )
    if not selected:
        print("未选择任何课堂")
        sys.exit(1)
    return [c["id"] for c in selected]


COOKIE_STRING, UNIVERSITY_ID = _ensure_login()

# ── 配置 ────────────────────────────────────────────────────────────

# PDF 保存根目录（每个课堂自动创建子目录）
if getattr(sys, 'frozen', False):
    OUTPUT_DIR = os.path.join(os.path.dirname(sys.executable), "ppt_downloads")
else:
    _proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUTPUT_DIR = os.path.join(_proj_root, "ppt_downloads")

# ============================================================
#   以下内容无需修改
# ============================================================

BASE_URL = "https://changjiang.yuketang.cn"


def parse_cookies(cookie_str: str) -> dict:
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies


def build_session(cookies: dict, classroom_id: str) -> requests.Session:
    csrf_token = cookies.get("csrftoken", "")
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "User-Agent": USER_AGENT,
        "X-CSRFToken": csrf_token,
        "X-Client": "web",
        "Xt-Agent": "web",
        "classroom-id": classroom_id,
        "university-id": UNIVERSITY_ID,
        "uv-id": UNIVERSITY_ID,
        "xtbz": "ykt",
        "Referer": f"{BASE_URL}/v2/web/studentLog/{classroom_id}",
    })
    return session


def get_lesson_list(session: requests.Session, classroom_id: str) -> list:
    """获取课堂全部课程记录，支持翻页"""
    lessons = []
    page = 0
    while True:
        resp = session.get(
            f"{BASE_URL}/v2/api/web/logs/learn/{classroom_id}",
            params={"actype": 14, "page": page, "offset": 20, "sort": -1},
        )
        data = resp.json()
        if data.get("errcode") != 0:
            print(f"  [错误] 获取课程列表失败: {data}")
            break
        activities = data["data"].get("activities", [])
        lessons.extend(activities)
        if not data["data"].get("has_more", False):
            break
        page += 1
        time.sleep(0.5)
    return lessons


def get_presentation_ids(session: requests.Session, lesson_id: str) -> list:
    resp = session.get(
        f"{BASE_URL}/api/v3/classroom-report/student/lesson-info",
        params={"lesson_id": lesson_id, "front_time": int(time.time() * 1000)},
    )
    data = resp.json()
    if data.get("code") != 0:
        print(f"  [警告] 获取 presentation 列表失败: {data.get('msg')}")
        return []
    return data["data"].get("presentationIds", [])


def get_slides(session: requests.Session, lesson_id: str, presentation_id: str) -> list:
    resp = session.get(
        f"{BASE_URL}/api/v3/classroom-report/student/ppt",
        params={
            "lesson_id": lesson_id,
            "presentationId": presentation_id,
            "front_time": int(time.time() * 1000),
        },
    )
    data = resp.json()
    if data.get("code") != 0:
        print(f"  [警告] 获取幻灯片失败: {data.get('msg')}")
        return []
    slides = sorted(data["data"].get("slideList", []), key=lambda s: s["index"])
    return [{"index": s["index"], "cover": s["cover"]} for s in slides]


def download_image(session: requests.Session, url: str) -> bytes | None:
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.content
        print(f"\n  [警告] 图片下载失败 HTTP {resp.status_code}: {url}")
    except Exception as e:
        print(f"\n  [警告] 图片下载异常: {e}")
    return None


def images_to_pdf(image_bytes_list: list, output_path: str) -> bool:
    pil_images = []
    for img_bytes in image_bytes_list:
        if not img_bytes:
            continue
        try:
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")
            pil_images.append(img)
        except Exception as e:
            print(f"  [警告] 图片解码失败: {e}")
    if not pil_images:
        return False
    pil_images[0].save(
        output_path, save_all=True, append_images=pil_images[1:], format="PDF"
    )
    return True


def safe_filename(name: str) -> str:
    invalid = r'\/:*?"<>|'
    return "".join(c if c not in invalid else "_" for c in name).strip()


def _select_lessons(lessons: list) -> list:
    """交互选择要下载的课件，返回选中的 lesson 列表"""
    from datetime import datetime

    def _label(lesson):
        ts = lesson.get("create_time", 0)
        date_str = ""
        if ts:
            try:
                date_str = datetime.fromtimestamp(ts / 1000).strftime("%m-%d %H:%M")
            except Exception:
                pass
        return f"{date_str}  {lesson.get('title', '')}"

    return _interactive_select(lessons, label_fn=_label)


def _download_lesson(session, lesson, idx, total, classroom_dir):
    """下载单节课的全部 PPT"""
    lesson_id = lesson["courseware_id"]
    title = lesson["title"]

    pres_ids = get_presentation_ids(session, lesson_id)
    if not pres_ids:
        print(f"  无 PPT，跳过")
        return

    for p_idx, pres_id in enumerate(pres_ids):
        suffix = f"_P{p_idx + 1}" if len(pres_ids) > 1 else ""
        fname = safe_filename(title) + suffix + ".pdf"
        out_path = os.path.join(classroom_dir, fname)

        if os.path.exists(out_path):
            print(f"  已存在，跳过: {fname}")
            continue

        slides = get_slides(session, lesson_id, pres_id)
        if not slides:
            print("  无幻灯片，跳过")
            continue

        print(f"  下载 {len(slides)} 张幻灯片 …")
        images = [None] * len(slides)
        # 线程池并发下载，4 线程
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(download_image, session, slide["cover"]): i
                for i, slide in enumerate(slides)
            }
            done = 0
            for future in as_completed(futures):
                idx = futures[future]
                images[idx] = future.result()
                done += 1
                print(f"    第 {done}/{len(slides)} 张", end="\r", flush=True)

        print()
        if images_to_pdf(images, out_path):
            print(f"  保存成功: {fname}")
            logging.info("下载完成: %s (%d 页)", fname, len(images))
        else:
            print(f"  [错误] PDF 生成失败")
            logging.error("PDF 生成失败: %s", fname)
        time.sleep(0.3)


def _pick_lessons_for_classroom(cookies: dict, classroom_id: str):
    """获取课堂课件列表并交互选课，返回 (session, selected_lessons) 或 (None, [])"""
    session = build_session(cookies, classroom_id)

    print(f"\n正在获取课件列表（课堂 {classroom_id}）…")
    lessons = get_lesson_list(session, classroom_id)
    if not lessons:
        print("  [错误] 未能获取到任何课件。")
        return session, []

    return session, _select_lessons(lessons)


def main():
    classroom_ids = _resolve_classroom_ids()

    if not classroom_ids:
        print("[错误] 未指定任何课堂 ID。")
        sys.exit(1)

    cookies = parse_cookies(COOKIE_STRING)
    root = Path(OUTPUT_DIR)

    logging.info("开始下载，共 %d 个课堂", len(classroom_ids))

    # 第一阶段：逐个课堂选课
    plan = []  # [(classroom_id, session, selected_lessons)]
    for cid in classroom_ids:
        session, selected = _pick_lessons_for_classroom(cookies, cid)
        if selected:
            plan.append((cid, session, selected))

    if not plan:
        print("\n未选择任何课件，退出。")
        sys.exit(0)

    # 第二阶段：统一下载
    total_lessons = sum(len(sel) for _, _, sel in plan)
    print(f"\n{'=' * 50}")
    print(f"总计 {len(plan)} 个课堂，{total_lessons} 节课件")
    print(f"{'=' * 50}")

    for cid, session, selected in plan:
        classroom_dir = str(root / cid) if len(classroom_ids) > 1 else str(root)
        Path(classroom_dir).mkdir(parents=True, exist_ok=True)

        print(f"\n── 课堂 {cid} ({len(selected)} 节) ──")
        for idx, lesson in enumerate(selected):
            print(f"[{idx + 1}/{len(selected)}] {lesson['title']}")
            _download_lesson(session, lesson, idx, len(selected), classroom_dir)
            print()

    print("全部完成！文件保存在:", root.resolve())
    logging.info("全部完成，共 %d 个课堂 %d 节课件，保存至 %s", len(plan), total_lessons, root.resolve())


if __name__ == "__main__":
    main()
