# fuckCourse 更新日志

## v3.1.0-dev (2026-06-27)

### 新增
- zhs: AI 课程接入主流程 — 菜单 `[3]` 交互式课程选择，统一展示知到/共享课/AI 课程
- zhs: `_interactive_select_courses()` — 运行时获取全部课程列表，编号展示，支持多选/全选/退出

### 重构
- zhs: `--aicourse` / `--noexam` CLI 参数移除，AI 课程改为自动检测
- zhs: `--fetch` CLI 参数移除，`execution.json` 文件缓存机制移除，改为运行时交互式选择
- zhs: `FUCKCOURSE_EXEC` 环境变量移除
- zhs: `_validate_ai_config()` / `_validate_openai_config()` / `_validate_ppt_config()` 提取为模块级函数
- zhs: `fuckWhatever()` 增加 `aiConfig` 参数，自动包含 AI 课程
- zhs: `import re` 移除（不再需要 execution.json 类型回退推断）

### 修复
- zhs: AI 课程与普通课程统一交互式选择，无需手动 `--fetch` 生成缓存文件

### 性能
- zhs: AI 配置验证失败在自动检测路径中只警告跳过，不阻塞普通课程

### 其他
- 版本号 v3.0.0-dev → v3.1.0-dev
- README: 新增 AI 配置文档；移除 yuketang CLI 参数示例（统一菜单驱动）；移除 execution.json 文档

---

## v3.0.0-dev (2026-06-14)

### 修复
- PyInstaller frozen: 子模块加载从 `subprocess.run()` 改为进程内 `exec(compile(...))`，解决 exe 在其他电脑上子进程双开竞争 stdin 导致闪退的问题
- zhs: `exit` 注入 `exec()` 命名空间，修复 `name 'exit' is not defined`
- PyInstaller spec: 使用 `sys.prefix` 动态定位 DLL，避免硬编码 `CONDA_PREFIX`
- PyInstaller spec: `collect_submodules()` 递归收集 chardet / charset_normalizer / fontTools / Crypto 子模块，根除 `No module named` 错误

### 架构
- 新增 `_run_frozen()` — frozen 模式用 `exec()` 进程内加载模块脚本，`_ns` 注入 `exit` 兼容 zhs
- 新增 `_setup_env()` — 统一环境变量注入 + `logs/` 目录创建
- 开发模式保留 `_run_subprocess()`，通过 `_python_exe()` 调用 conda python

## v3.0.0 (2026-06-13)

### 新增
- yuketang: 微信扫码登录，启动自动检测 cookies 过期/缺失 → 弹 QR 码登录
- yuketang: 终端 ASCII 渲染 QR 码（移植自 zhs `showImage`，内嵌到 `yuketang_login.py`）
- yuketang: `yuketang_login.py` — `qr_login()` 完整扫码流程（pre-info → 显示 QR → 轮询 → 保存）
- yuketang: `fetch_classroom_list()` — `/v2/api/web/courses/list?identity=2` 获取学生全部课程
- yuketang: `validate_cookies()` — `/v2/api/web/userinfo` 验证 cookies
- yuketang: 交互式课堂选择（多选逗号分隔 / 全选 `a` / 退出 `q`）
- yuketang: 交互式课件选择（多选逗号分隔 / 全选 `a` / 退出 `q`）
- yuketang: 多课堂时先逐个选课 → 收集完毕后统一下载
- yuketang: `university_id` 自动提取，从课程 API `course.university_id` 获取，过滤为 0 的非正式课程
- yuketang: 配置文件 `yuketang_config.py` → `yuketang_config.json`（`cookies` / `university_id` / `classroom_ids`）
- yuketang: 接入主系统统一启动器 `main.py` 菜单 `[4]`
- yuketang: 接入共享 `config.json` / `cookies.json`（通过 `FUCKCOURSE_CONFIG` / `FUCKCOURSE_COOKIES` 环境变量）
- yuketang: 日志输出到 `logs/yuketang.log`（通过 `FUCKCOURSE_LOG_DIR` 环境变量）
- yuketang: `yuketang-ppt-downloader/` 重命名为 `yuketang/`，`download_ppt.py` → `main.py`

### 反向工程
- yuketang: QR 登录 API — `GET /api/v3/user/login/pre-info` + `POST /api/v3/user/login`
- yuketang: 课程列表 API — `/v2/api/web/courses/list?identity=2`（identity=1 教的课，2 听的课）
- yuketang: 课件列表 API — `/v2/api/web/logs/learn/{id}?actype=14`
- yuketang: PPT 下载 API — `/api/v3/classroom-report/student/ppt`

## v2.2.2 (2026-06-12)

### 新增
- 统一日志目录 `logs/`，所有平台日志输出到根目录
- welearn: 接入 `logging` 模块，文件日志 `logs/welearn.log`
- welearn: 关键操作（登录、提交、异常）写入日志，静默异常补 `exc_info`

### 修复
- 编译后日志不可见：chaoxing/zhs 日志原本在模块目录（`_MEIPASS` 内），改为 `FUCKCOURSE_LOG_DIR` 环境变量指向 `DATA_DIR/logs/`
- chaoxing: `logger.py` 日志路径改为 `{LOG_DIR}/chaoxing.log`
- zhs: `logger.py` 日志路径改为 `{LOG_DIR}/zhs_logs/`

### 结构
```
logs/
├── chaoxing.log
├── welearn.log
└── zhs_logs/
    ├── debug.log / info.log / warning.log / error.log / critical.log
```

## v2.2.1 (2026-06-12)

### 新增
- welearn: 时长模式进度条 (`progressbar_view`)，多线程每行独立进度条，格式 `|#####     | 50.0% (15/30秒)`
- welearn: 课程目录树 (`tree_view`)，3 级结构 课程→单元→SCO，`[未开放]`/`[已完成]` 标签
- welearn: `print_course_tree()` 递归打印，SCO 数据缓存避免重复请求

### 修复
- PyInstaller: frozen 模式下拆分为 `APP_DIR`（`_MEIPASS`，代码）+ `DATA_DIR`（`sys.executable`，用户数据），修复 `[WinError 267] 目录名称无效`
- main.py: 图标路径修正为 `icon/icon.ico`
- main.py: `interrupted by user` / `按任意键` 提示统一左对齐

### 踩坑：PyInstaller 路径问题
- **v2.1.0 的"修复"引入新 bug**：v2.1.0 把 ROOT 从 `__file__` 改成 `sys.executable` 以解决 config 找不到，但这导致模块目录（chaoxing/zhs/welearn）也指向 exe 目录——而 PyInstaller 打包的 data 实际解压在 `_MEIPASS`，于是报 `目录名称无效`
- **正确做法**：frozen 下必须两条路径——代码目录用 `sys._MEIPASS`，用户数据目录用 `os.path.dirname(sys.executable)`，不能混用
- **图标**：`.gitignore` 忽略了 `icon/` 目录，编译命令路径也写错了（`icon\fuckCourse.ico` 实际是 `icon/icon.ico`），spec 没配 `icon=` 参数

## v2.2.0 (2026-06-12)

### 新增
- chaoxing: 课程目录树形视图 (`tree_view`)，对齐 ZHS 风格
- chaoxing: `decode_course_point()` 保留章节层级，新增 `_extract_section_tree()` 递归构建章→节→子节结构
- chaoxing: `print_course_tree()` / `_print_section()` 递归打印，已完成项标注 `[已完成]`
- chaoxing: `tree_view` 配置开关，默认开启，关闭则跳过打印

### 优化
- chaoxing: 树形打印增加分隔线，层级间距对齐 ZHS，不再紧凑

## v2.1.0 (2026-06-12)

### 新增
- 统一 config.json / cookies.json 架构，三平台各自读写自己的 section
- 首次运行自动创建 config.json 并写入完整默认字段
- 账号密码登录后自动回写 config，下次免输入
- WE Learn 自动登录：config 凭据 → 交互输入，去掉 cookie 登录步骤
- WE Learn 登录移到模式选择前面

### 修复
- chaoxing: config.json 不存在时不再返回 None，改为创建文件
- chaoxing: use_cookies 默认值改为 True，二次运行免登录
- chaoxing: cookie 过期自动提示重新输入并保存
- chaoxing: config 写入所有完整字段（tiku/notification）
- welearn: sso_login 中 extraCheck 为 null 时崩溃
- welearn: 每次登录后无条件保存 cookies
- PyInstaller: frozen 模式下 ROOT 改用 sys.executable，修复 exe 找不到 config/cookies

### 清理
- 删除 config_bridge.py
- 删除 chaoxing/config_template.ini
- 删除 zhs/meta.json（去掉更新检测）
- 删除各子目录残留的 config.ini / cookies.json / cookies.txt
- welearn: 删除开发者姓名、QQ、邮箱等菜单文案

## v2.0.0 (2026-06-10)

### 新增
- 统一启动器 main.py，菜单选择三平台
- subprocess 调度，stdin/stdout/stderr 透传
- 环境变量 FUCKCOURSE_CONFIG / FUCKCOURSE_COOKIES 传递路径
- WE Learn cookie 持久化

### 技术栈
- Python 3.13 (Conda: fuckcourse)
- PyInstaller 6.20.0 打包为单文件 exe
