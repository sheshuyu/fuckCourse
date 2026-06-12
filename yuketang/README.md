# yuketang-ppt-downloader

> 长江雨课堂 PPT 批量下载器

通过雨课堂 Web API 抓取课件图片，合并为每课时一个 PDF 文件。支持多课堂批量下载、断点续传（已下载文件自动跳过）、命令行 / 配置文件 / 交互式三种使用方式。仅需浏览器 Cookie，无需模拟登录。

## 实现思路

雨课堂的课件以幻灯片图片形式存储在 CDN，浏览器端通过 API 分三步拿到图片 URL：

```
课堂 ID
  └─ GET /v2/api/web/logs/learn/{classroom_id}
        获取该课堂所有课程记录（lesson），每条记录含 courseware_id 和标题
        └─ GET /api/v3/classroom-report/student/lesson-info?lesson_id=...
              获取该节课包含的 PPT ID 列表（presentationIds）
              └─ GET /api/v3/classroom-report/student/ppt?lesson_id=&presentationId=...
                    获取每张幻灯片的封面图 URL（slideList[].cover）
```

拿到图片 URL 后，逐张下载为 JPEG，再用 Pillow 合并成 PDF，一个 PPT 对应一个 PDF 文件。

身份验证依赖浏览器 Cookie（`sessionid`、`csrftoken` 等），无需模拟登录。

## 环境依赖

```bash
pip install requests Pillow
```

## 配置方法

**第一步：填写 Cookie**

1. 复制 `yuketang_config.example.py` 为 `yuketang_config.py`（同目录下）
2. 浏览器登录 [changjiang.yuketang.cn](https://changjiang.yuketang.cn)
3. `F12` → Network → 任意请求 → Request Headers → `Cookie` 字段 → 右键 **Copy value**
4. 粘贴到 `yuketang_config.py` 的 `COOKIE_STRING`

> `yuketang_config.py` 已加入 `.gitignore`，不会被提交。如果 Cookie 失效（通常 `sessionid` 有效期较短），重新复制粘贴即可。

**第二步：获取课堂 ID**

打开某门课的学习记录页面，URL 中的数字即为课堂 ID：

```
https://changjiang.yuketang.cn/v2/web/studentLog/12345678
                                                  ^^^^^^^^
                                                  classroom_id
```

**第三步：填写课堂 ID**

打开 `download_ppt.py`，修改 `CLASSROOM_IDS`：

```python
CLASSROOM_IDS = [
    "12345678",   # 课堂 A
    "87654321",   # 课堂 B（按需添加）
]
```

## 使用方法

```bash
# 方式 A：按配置文件中的 CLASSROOM_IDS 下载
python download_ppt.py

# 方式 B：命令行传入课堂 ID（逗号分隔），临时覆盖配置
python download_ppt.py 12345678,87654321

# 方式 C：运行后交互输入（CLASSROOM_IDS 为空时自动触发）
python download_ppt.py
> 请输入课堂 ID（多个用逗号分隔）: 12345678,87654321
```

## 输出结构

单个课堂时，PDF 直接保存在 `ppt_downloads/`；多个课堂时按课堂 ID 分子目录：

```
ppt_downloads/
├── 12345678/
│   ├── 第一章 绪论.pdf
│   ├── 第二章 基础知识.pdf
│   └── ...
└── 87654321/
    ├── Lecture 01 Introduction.pdf
    └── ...
```

已下载的文件会自动跳过，中断后重跑不会重复下载。

## 注意事项

- Cookie 有时效，失效后重新从浏览器复制即可
- 下载间隔已内置限速（图片 50ms、PPT 间 300ms），无需额外调整
- 仅供个人学习使用，请勿传播课件
