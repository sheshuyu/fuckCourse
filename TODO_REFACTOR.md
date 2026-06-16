# TODO: 代码优化清单

> 审计日期：2026-06-16

---

## 🔴 僵尸代码（删除即可，无风险） ✅ 已清理

### chaoxing

- [x] ~~`chaoxing/api/__init__.py`~~ — 已删除
- [x] ~~`chaoxing/api/captcha.py`~~ — 已删除（139行）
- [x] ~~`chaoxing/api/notification.py`~~ — 已删除（320行）
- [ ] `chaoxing/api/base.py:222-227` — `ActivityStatus` / `ActivityType` 枚举 ⚠️ 未完善功能，暂保留
- [ ] `chaoxing/api/base.py:354-420` — `get_activity_list()` / `pre_sign()` / `sign_in_normal()` ⚠️ 签到功能未完成，暂保留
- [x] ~~`chaoxing/api/exceptions.py`~~ — `MaxRollBackExceeded` + `JSONDecodeError` 导入已删除
- [x] ~~`chaoxing/api/process.py`~~ — 已删除（62行）

### zhs

- [x] ~~`zhs/fucker.py:254-296`~~ — 注释掉的 WebSocket QR 登录已删除
- [x] ~~`zhs/fucker.py:743-770`~~ — `saveDatabaseIntervalTime` V1 已删除
- [x] ~~`zhs/fucker.py:585,822-851`~~ — `if False` + `saveCacheIntervalTime` 已删除
- [x] ~~`zhs/fucker.py:658`~~ — `queryStudyReadBefore` 已删除
- [x] ~~`zhs/utils.py:14`~~ — `strToClass()` 已删除
- [x] ~~`zhs/zd_utils.py:79`~~ — `revEv()` 已删除
- [x] ~~`zhs/logger.py:128-133`~~ — `getLogger()` + `_logger_map` 已删除

### welearn

- [x] ~~`welearn/welearn_decompiled.py:91`~~ — `load_welearn_cookies()` 已删除
- [x] ~~`welearn/welearn_decompiled.py:105`~~ — `validate_cookies()` 已删除
- [x] ~~`welearn/welearn_decompiled.py:573`~~ — `login_time()` 已删除
- [x] ~~`welearn/welearn_decompiled.py:577`~~ — `login_course()` 已删除

### yuketang

- [x] ~~`yuketang/main.py:25`~~ — `parse_cookie_string` 已从 import 移除

---

## 🟡 未使用的 import ✅ 已清理

- [x] ~~`chaoxing/api/live.py:4`~~ — `from urllib import parse` 已删除
- [x] ~~`chaoxing/api/live_process.py:1,3,6,7`~~ — 重复 `time`、`gc`、`threading` 已删除
- [x] ~~`chaoxing/api/exceptions.py:2-4`~~ — `JSONDecodeError` try/except 已删除
- [x] ~~`zhs/main.py:2,5`~~ — `import re` / `import requests` 已删除

---

## 🟠 重复代码

- [x] ~~`yuketang/yuketang_login.py` vs `yuketang/main.py`~~ — cookie 解析器保留两份（不同模块，避免循环导入）
- [x] ~~`chaoxing/main.py:199` vs `chaoxing/api/base.py:121`~~ — 凭据保存合并到 `_save_credentials_to_config`
- [x] ~~`chaoxing/api/answer.py:1005,1157`~~ — `remove_md_json_wrapper` 提为模块级 `_remove_md_json_wrapper`
- [ ] `chaoxing/api/base.py:841` vs `chaoxing/api/answer_check.py:61` — `multi_cut` / `cut` 共享 `cut_char` 列表（`multi_cut` 已调用 `cut`，仅 `cut_char` 定义重复，影响小）
- [x] ~~`zhs/fucker.py:447-451,952-956,1279`~~ — 终端宽度 → `_get_term_width()`
- [x] ~~`zhs/fucker.py:507,763,811,844`~~ — `b64encode(token_id)` → `_encode_token()`
- [x] ~~`zhs/fucker.py:161-163,375-377,878-880`~~ — Origin/Referer 头 → `_set_origin_referer()`
- [x] ~~`welearn/welearn_decompiled.py:331-355,481-505`~~ — `cmi_data` JSON blob → `_build_cmi_data()`
- [x] ~~`welearn/welearn_decompiled.py:652-668,679-696`~~ — 重试+退避逻辑重复 → ⚠️ 模式相似但不完全相同，暂保留
- [x] ~~`welearn/welearn_decompiled.py` + `yuketang/`~~ — User-Agent 6 处 → `USER_AGENT` 常量（welearn 定义，yuketang 已有复用）
- [x] ~~`yuketang/main.py:85-115,275-298`~~ — 多选菜单 → `_interactive_select()`

---

## 🔴 性能问题

### 高影响

- [x] ~~`chaoxing/api/answer.py:219`~~ — `CacheDAO` 单例 + 内存缓存，`get_cache` 零 I/O
- [x] ~~`chaoxing/api/base.py:462`~~ — 卡片遍历早停：连续 2 轮空返则 break
- [x] ~~`chaoxing/api/base.py:694-738`~~ — 视频忙等优化：计算精确等待时间，替代每秒 sleep
- [x] ~~`yuketang/main.py:327-330`~~ — PPT 图片 ThreadPoolExecutor 4 线程并发下载

### 中影响

- [x] ~~`chaoxing/api/base.py:662-663`~~ — ⚠️ 实际是 `_refresh_video_status` 和 `study_video` 分别构造同一 URL（不同调用路径），非重复请求
- [ ] `chaoxing/api/base.py:776-1148` — `study_work()` 内 9 个内嵌函数每次调用重新编译，应提升为模块级
- [x] ~~`welearn/welearn_decompiled.py:538,702,893`~~ — `_get_welearn_config_cached()` 首次读后缓存
- [x] ~~`zhs/fucker.py:1590-1629`~~ — ⚠️ `readAnswerCache` 仅调用一次，已存 `self.answerCache` 内存中，无需优化

### 低影响

- [x] ~~`zhs/fucker.py:1826`~~ — 缓存命中后去掉 `sleep(3-5s)`
- [ ] `zhs/fucker.py:1076-1086` — `_apiQuery` 中 Content-Type 头在并发场景下可能竞态（低影响，暂不改）
- [x] ~~`zhs/push.py:14,19`~~ — 推送请求添加 `timeout=15`

---

## 🟡 屎山重构

- [ ] `welearn/welearn_decompiled.py:584-979` — `__main__` 块 396 行，7 层嵌套。拆分为独立函数（大重构，单独 PR）
- [ ] `zhs/fucker.py` — 2345 行巨石文件，4 个类各自拆成独立模块（大重构，单独 PR）
- [ ] `chaoxing/api/base.py:776-1148` — `study_work()` 372 行，带 FIXME 注释。拆成独立类（大重构，单独 PR）
- [ ] `welearn/welearn_decompiled.py:128-134` — 模块级全局变量 `uid`/`cid`/`way1Succeed` 等，多线程无锁访问（需深入理解线程模型）
- [x] ~~`yuketang/main.py:120`~~ — `COOKIE_STRING, UNIVERSITY_ID = _ensure_login()` → 延迟初始化 `_get_cookies()`/`_get_uni_id()`
- [x] ~~`zhs/push.py:15`~~ — pushplus HTTP → HTTPS

---

## 🟢 小修小补

- [x] ~~`main.py:23`~~ — 硬编码 conda 路径已移除，始终用 `sys.executable`
- [x] ~~`main.py:30`~~ — `os.system("cls")` → ANSI `\033[2J\033[H`
- [x] ~~`main.py:74,92-96`~~ — KeyboardInterrupt 内 `input()` 移到独立的 `print()` 后，避免二次 Ctrl+C 吞异常
- [x] ~~`chaoxing/api/answer.py:1099`~~ — 裸 `except:` → `except Exception:`
- [ ] `chaoxing/main.py:95-139` — 默认配置值全存为字符串，应使用原生类型（⚠️ 改配置格式，单独 PR）
- [ ] `chaoxing/api/answer.py:183-184` — `"".split(',')` 返回 `['']` 而非 `[]`（⚠️ 未能定位实际代码行）
- [x] ~~`chaoxing/api/config.py:21`~~ — `THRESHOLD = 1` → `POLL_INTERVAL = 1`
- [ ] `zhs/logger.py:66-67` — `exception` 属性命名（⚠️ 非功能性 bug，改属性名会破坏 22 处调用）
- [ ] `zhs/fucker.py:1115` — `zhidaoAiExamQuery` 不是无意义包装：相比 `zhidaoQuery` 多了 `_checkCookies()`+`_sessionReady()`
- [x] ~~`zhs/zd_utils.py:20,24`~~ — staticmethod `self.pad()`/`self.unpad()` → `Cipher.pad()`/`Cipher.unpad()`
- [ ] `zhs/fucker.py` — 14 个 magic number 应提为常量（⚠️ 需逐一定位替换，单独 PR）
- [ ] `welearn/welearn_decompiled.py` — 11 个裸 `except Exception:`（⚠️ 部分已有日志，剩余影响小）
- [x] ~~`yuketang/main.py:261`~~ — 函数内 `import datetime` 移到文件顶部
- [x] ~~`yuketang/yuketang_login.py:34`~~ — `_show_image` 死参数 `show_in_terminal` 已移除
