# fuckCourse v2.2.2

超星学习通 / WE Learn / 智慧树 三合一自动刷课工具。

## 项目结构

```
├── main.py                  # 统一启动器，菜单选择平台 (subprocess 调度)
├── config.json              # 统一配置（首次运行自动生成）
├── cookies.json             # 统一 cookies（登录后自动保存）
├── requirements.txt         # Python 依赖
├── log.md                   # 更新日志
├── logs/                    # 运行日志（自动生成）
│   ├── chaoxing.log
│   ├── welearn.log
│   └── zhs_logs/
│
├── chaoxing/                # 超星学习通
│   ├── main.py              # 入口
│   ├── api/                 # 核心模块
│   │   ├── base.py          # 课程/视频/文档/作业处理
│   │   ├── answer.py        # 题库（多 provider）
│   │   ├── decode.py        # HTML 解析（课程列表/章节树/任务点）
│   │   ├── process.py       # 章节调度
│   │   ├── live.py          # 直播处理
│   │   ├── captcha.py       # 验证码识别
│   │   ├── cipher.py        # 加密
│   │   ├── cookies.py       # Cookie 管理
│   │   ├── notification.py  # 消息推送
│   │   └── ...
│   └── resource/            # 资源文件
│
├── welearn/                 # WE Learn
│   └── welearn_decompiled.py  # 一体版（SSO 登录 + 课程/时长刷取）
│
└── zhs/                     # 智慧树
    ├── main.py              # 入口
    ├── fucker.py            # 核心刷课逻辑
    ├── utils.py             # 工具（进度条等）
    ├── sign.py              # 签到
    ├── push.py              # 推送通知
    └── logger.py            # 日志
```

## 功能

| 平台 | 课程刷取 | 时长刷取 | 自动答题 | 自动签到 | 通知推送 |
|------|:---:|:---:|:---:|:---:|:---:|
| 超星学习通 | Y | Y | Y | Y | Y |
| WE Learn | Y | Y | — | — | — |
| 智慧树 | Y | Y | Y | — | Y |

## 运行
1.release下载exe文件,双击运行 

2.或者运行python脚本
```bash
pip install -r requirements.txt
python main.py
```

## 使用流程

启动后进入主菜单选择平台，每个平台内部有自己的交互菜单（选择课程/时长模式、输入 ID 等）：

```
==================================================
             fuckCourse v2.2.2
             designed by snake
==================================================

  [1] 超星学习通 (Chaoxing)
  [2] WE Learn (SFLEP)
  [3] 智慧树 (ZHS)
  [0] 退出

  请选择平台 (0-3):
```

所有配置从 `config.json` 读取，无需传参。各平台运行完毕后返回主菜单。

## 登录策略

```
启动 → cookies.json 存在且有效？
  ├─ 是 → 跳过登录，直接刷课
  └─ 否 → config.json 有 username/password？
           ├─ 是 → 自动登录 → 保存 cookies.json
           └─ 否 → 交互输入 → 登录 → 保存 cookies.json + 回写 config.json
```

切换账号：删除 `cookies.json`，或在 `config.json` 中修改 `username`/`password` 后重启。

## 配置

直接编辑 exe 同目录下的 `config.json`。首次运行任一平台后自动生成，账号密码登录成功后自动回写。

### chaoxing — 超星学习通

**common（基本配置）**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `username` | string | `""` | 手机号账号 |
| `password` | string | `""` | 登录密码 |
| `course_list` | array | `[]` | 课程 ID 列表，如 `["2151141"]`，留空手动选择 |
| `speed` | number | `1.0` | 视频倍速，最大 2 |
| `jobs` | number | `4` | 并发章节数 |
| `notopen_action` | string | `"retry"` | 未开放章节：`retry` 重试 / `continue` 跳过 |

**tiku（题库配置）**

不配 `provider` 则不答题，测验直接跳过。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `provider` | string | `""` | 题库来源 |
| `submit` | boolean | `false` | 是否自动提交答题 |
| `cover_rate` | number | `0.8` | 最低覆盖率（搜到/总题数） |
| `delay` | number | `1.0` | 多题搜索间隔（秒） |
| `true_list` | string | `"正确,对,√,是"` | 判断题"对" |
| `false_list` | string | `"错误,错,×,否"` | 判断题"错" |

Provider 可选项：

| 值 | 说明 | 需额外配置 |
|----|------|-----------|
| `TikuYanxi` | 言溪题库 | `tokens` |
| `TikuLike` | LIKE 知识库 | `tokens`, `likeapi_*` |
| `TikuAdapter` | 自建题库 | `url` |
| `AI` | OpenAI 兼容 API | `endpoint`, `key`, `model` |
| `SiliconFlow` | 硅基流动 | `siliconflow_key`, `siliconflow_model` |

各 provider 专属字段：

| 字段 | provider | 说明 |
|------|----------|------|
| `tokens` | TikuYanxi / TikuLike | API Token，多个逗号分隔 |
| `likeapi_model` | TikuLike | 模型名，默认 `"glm-4.5-air"` |
| `url` | TikuAdapter | 适配器服务地址 |
| `endpoint` | AI | API 地址（如 `https://api.openai.com/v1`） |
| `key` | AI | API Key |
| `model` | AI | 模型名（如 `gpt-4o`） |
| `http_proxy` | AI | HTTP 代理（选填） |
| `min_interval_seconds` | AI | 请求间隔，默认 `3` |
| `siliconflow_key` | SiliconFlow | API Key |
| `siliconflow_model` | SiliconFlow | 模型名，默认 `deepseek-ai/DeepSeek-V3` |

**notification（通知配置）**

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `provider` | `""` | `ServerChan` / `Qmsg` / `Bark` / `Telegram` |
| `url` | `""` | 通知服务 URL |

URL 格式：

| provider | 格式 |
|----------|------|
| ServerChan | `https://sctapi.ftqq.com/<key>.send` |
| Qmsg | `https://qmsg.zendee.cn/send/<key>` |
| Bark | `https://api.day.app/<key>/` |
| Telegram | `https://api.telegram.org/bot<token>/sendMessage`（需同时填 `tg_chat_id`） |

### welearn — WE Learn (SFLEP)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `username` | string | `""` | WE Learn 账号 |
| `password` | string | `""` | 登录密码 |
| `save_cookies` | boolean | `true` | 是否持久化 cookies |
| `tree_view` | boolean | `true` | 选课后打印课程目录树 |
| `progressbar_view` | boolean | `true` | 时长模式显示进度条 |

### zhs — 智慧树

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `username` | string | `""` | 智慧树账号 |
| `password` | string | `""` | 登录密码 |
| `qrlogin` | boolean | `true` | 优先二维码登录 |
| `save_cookies` | boolean | `true` | 是否持久化 cookies |
| `logLevel` | string | `"INFO"` | 日志级别：`"DEBUG"` / `"INFO"` |
| `proxies` | object | `{}` | 代理，如 `{"http": "http://127.0.0.1:8080"}` |

**qr_extra（二维码显示选项）**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `show_in_terminal` | boolean/null | `null` | `true` 终端 / `false` 弹窗 / `null` 自动 |
| `ensure_unicode` | boolean | `false` | 仅用 Unicode 字符打印 |

**pushplus（推送通知）**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable` | boolean | `false` | 启用 PushPlus |
| `token` | string | `""` | PushPlus Token |

**bark（推送通知）**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable` | boolean | `false` | 启用 Bark（iOS） |
| `token` | string | `""` | Bark URL |

## 打包 exe

```bash
pip install pyinstaller

pyinstaller --onefile --console -p . --name fuckCourse \
  --add-data "chaoxing;chaoxing" \
  --add-data "zhs;zhs" \
  --add-data "welearn;welearn" \
  --add-binary "<conda_env>/Library/bin/ffi.dll;." \
  --add-binary "<conda_env>/Library/bin/libexpat.dll;." \
  --add-binary "<conda_env>/Library/bin/sqlite3.dll;." \
  --add-binary "<conda_env>/Library/bin/liblzma.dll;." \
  --add-binary "<conda_env>/Library/bin/libmpdec-4.dll;." \
  --add-binary "<conda_env>/Library/bin/libcrypto-3-x64.dll;." \
  --add-binary "<conda_env>/Library/bin/libssl-3-x64.dll;." \
  main.py
```

`<conda_env>` 替换为 conda 环境路径。首次 build 后生成 `fuckCourse.spec`，后续 rebuild 只需 `pyinstaller fuckCourse.spec`。

## 致谢

- 超星：基于 [Samueli924/chaoxing](https://github.com/Samueli924/chaoxing)
- WE Learn：基于 [Fanyuchang2026/welearn-helper](https://github.com/Fanyuchang2026/welearn-helper)
- 智慧树：基于 [VermiIIi0n/fuckZHS](https://github.com/VermiIIi0n/fuckZHS)

## 架构说明

v2.0+ 采用 subprocess 包装方案：`main.py` 通过 `subprocess.run()` 启动各平台并透传 stdin/stdout/stderr。通过环境变量 `FUCKCOURSE_CONFIG`、`FUCKCOURSE_COOKIES`、`FUCKCOURSE_LOG_DIR` 传递根目录路径，各平台直接读写对应 section 和日志。各平台完全独立运行，互不影响。

PyInstaller 打包时自动检测 `sys.frozen`：代码目录指向 `_MEIPASS`（解压的模块），用户数据（config/cookies/logs）指向 exe 所在目录。

## 免责声明

本工具仅供学习交流使用，请勿用于商业用途。使用本工具产生的任何后果由使用者自行承担。
