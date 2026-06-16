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

- [ ] `yuketang/yuketang_login.py:167` vs `yuketang/main.py:138` — cookie 字符串解析器两份完全相同的实现，保留一份
- [ ] `chaoxing/main.py:199` vs `chaoxing/api/base.py:121` — 凭据保存到 config.json 的逻辑重复
- [ ] `chaoxing/api/answer.py:1005,1157` — `remove_md_json_wrapper` 内嵌函数 copy-paste 两次
- [ ] `chaoxing/api/base.py:841` vs `chaoxing/api/answer_check.py:61` — 答案切分 `multi_cut` / `cut` 重复
- [ ] `zhs/fucker.py:447-451,952-956,1279` — 终端宽度获取逻辑重复 3 次
- [ ] `zhs/fucker.py:507,763,811,844` — `b64encode(str(token_id).encode()).decode()` 重复 4 次
- [ ] `zhs/fucker.py:161-163,375-377,878-880` — Origin/Referer 头设置重复 3 次
- [ ] `welearn/welearn_decompiled.py:331-355,481-505` — `cmi_data` JSON blob 重复（24行）
- [ ] `welearn/welearn_decompiled.py:652-668,679-696` — 重试+退避逻辑重复
- [ ] `welearn/welearn_decompiled.py` + `yuketang/` — User-Agent 字符串硬编码 6 处，提取为常量
- [ ] `yuketang/main.py:85-115,275-298` — 交互式多选菜单实现重复

---

## 🔴 性能问题

### 高影响

- [ ] `chaoxing/api/answer.py:219` — 每次查题新建 `CacheDAO()` → 读/写磁盘，50题=150次 I/O。应改为单例 + 内存缓存
- [ ] `chaoxing/api/base.py:462` — 每个章节固定遍历 `"0123456"` 7 个卡片号发 HTTP 请求，大部分章节仅 1-2 个。应早停
- [ ] `chaoxing/api/base.py:694-738` — 视频等待用 `while not passed` + `time.sleep(1)` 忙等，30-90秒视频产生大量无效循环。应用 `time.sleep(wait_time)` 替代
- [ ] `yuketang/main.py:327-330` — PPT 图片逐张阻塞下载，每张 sleep(0.05)。应用线程池并发

### 中影响

- [ ] `chaoxing/api/base.py:662-663` — 视频状态接口同一次调用中请求了两次
- [ ] `chaoxing/api/base.py:776-1148` — `study_work()` 内 9 个内嵌函数每次调用重新编译，应提升为模块级
- [ ] `welearn/welearn_decompiled.py:538,702,893` — 配置文件每次运行读 3 次，应缓存
- [ ] `zhs/fucker.py:1590-1629` — `readAnswerCache` 重试时重复读磁盘，应先检查内存缓存

### 低影响

- [ ] `zhs/fucker.py:1826` — 缓存命中后仍 `sleep(randint(3,5))` 模拟网络延迟，没必要
- [ ] `zhs/fucker.py:1076-1086` — `_apiQuery` 中 Content-Type 头在并发场景下可能竞态
- [ ] `zhs/push.py:14,19` — 推送请求无 `timeout`，可能永久阻塞

---

## 🟡 屎山重构

- [ ] `welearn/welearn_decompiled.py:584-979` — `__main__` 块 396 行，7 层嵌套。拆分为独立函数
- [ ] `zhs/fucker.py` — 2345 行巨石文件，4 个类各自拆成独立模块
- [ ] `chaoxing/api/base.py:776-1148` — `study_work()` 372 行，带 FIXME 注释。拆成独立类
- [ ] `welearn/welearn_decompiled.py:128-134` — 模块级全局变量 `uid`/`cid`/`way1Succeed` 等，多线程无锁访问
- [ ] `yuketang/main.py:120` — `COOKIE_STRING, UNIVERSITY_ID = _ensure_login()` 模块级副作用，import 时触发登录
- [ ] `zhs/push.py:15` — pushplus 使用明文 HTTP，Token 泄露风险

---

## 🟢 小修小补

- [ ] `main.py:23` — 硬编码 conda 路径 `D:\CondaEnvs\fuckcourse\python.exe`，应去掉或用 `CONDA_PREFIX` 推导
- [ ] `main.py:30` — `os.system("cls")` 可用 ANSI 转义序列替代，更快
- [ ] `main.py:74,92-96` — `except KeyboardInterrupt` 内调 `input()`，二次 Ctrl+C 会崩溃
- [ ] `chaoxing/api/answer.py:1099` — 裸 `except:` 会吞掉 `SystemExit`/`KeyboardInterrupt`
- [ ] `chaoxing/main.py:95-139` — 默认配置值全存为字符串，应使用原生类型（bool/int/float）
- [ ] `chaoxing/api/answer.py:183-184` — `"".split(',')` 返回 `['']` 而非 `[]`，应过滤空串
- [ ] `chaoxing/api/config.py:21` — `THRESHOLD = 1` 命名不清晰
- [ ] `zhs/logger.py:66-67` — `exception` 属性遮蔽 `logging.Logger.exception` 方法，容易误导
- [ ] `zhs/fucker.py:1115` — `zhidaoAiExamQuery` 是 `zhidaoQuery` 的无意义包装
- [ ] `zhs/zd_utils.py:20,24` — staticmethod 当实例方法调用
- [ ] `zhs/fucker.py` — 14 个 magic number 应提为常量（如 `0.0025`/`0.91`/`1.5`/`30`/`18`/`60`/`5` 等）
- [ ] `welearn/welearn_decompiled.py` — 11 个裸 `except Exception:` 无日志，排查困难
- [ ] `yuketang/main.py:261` — 函数内 `import datetime`，应移到文件顶部
- [ ] `yuketang/yuketang_login.py:34` — `_show_image` 的 `show_in_terminal` 参数永远是 `True`，死参数
