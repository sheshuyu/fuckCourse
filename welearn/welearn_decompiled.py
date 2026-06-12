"""
welearn一体版 - WELearn自动刷课工具 v4.0.0
适配2026年新SSO登录系统
"""
import os
import re
import json
import time
import random
import base64
from requests import Session
from threading import Thread

session = Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# Cookie 持久化
COOKIES_FILE = os.environ.get("FUCKCOURSE_COOKIES", "")
CONFIG_FILE = os.environ.get("FUCKCOURSE_CONFIG", "")

WELEARN_DEFAULTS = {
    "username": "",
    "password": "",
    "save_cookies": True,
    "progressbar_view": True,
    "tree_view": True,
}


def load_welearn_config():
    if not CONFIG_FILE or not os.path.isfile(CONFIG_FILE):
        return WELEARN_DEFAULTS.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        root = json.load(f)
    section = root.get("welearn", {})
    if not section:
        root["welearn"] = dict(WELEARN_DEFAULTS)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(root, f, indent=4, ensure_ascii=False)
        return WELEARN_DEFAULTS.copy()
    return section


def _save_welearn_credentials(username, password):
    if not CONFIG_FILE:
        return
    root = {}
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                root = json.load(f)
            except json.JSONDecodeError:
                root = {}
    section = root.get("welearn", {})
    section["username"] = username
    section["password"] = password
    root["welearn"] = section
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(root, f, indent=4, ensure_ascii=False)


def _read_root_cookies():
    if not COOKIES_FILE or not os.path.isfile(COOKIES_FILE):
        return {}
    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _write_root_cookies(data):
    if not COOKIES_FILE:
        return
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_welearn_cookies():
    root = _read_root_cookies()
    return root.get("welearn", {})


def save_welearn_cookies():
    root = _read_root_cookies()
    cookie_dict = {}
    for cookie in session.cookies:
        cookie_dict[cookie.name] = cookie.value
    root["welearn"] = cookie_dict
    _write_root_cookies(root)


def validate_cookies():
    try:
        resp = session.get(
            "https://welearn.sflep.com/student/index.aspx",
            timeout=10,
            allow_redirects=False,
        )
        if resp.status_code in (301, 302):
            location = resp.headers.get("Location", "")
            if "login" in location.lower():
                return False
        if resp.status_code == 200:
            return True
        return False
    except Exception:
        return False


def try_auto_login(username, password):
    print("[auto] 正在使用配置文件自动登录...")
    return sso_login(username, password)

# 全局变量
uid = None
cid = None
classid = None
way1Succeed = []
way2Succeed = []
way1Failed = []
way2Failed = []


def printline():
    print("---------------------------------------------------")


def progress_bar(elapsed, total, length=25, fill='#'):
    """返回进度条字符串: |#####     | 50.0%"""
    if total <= 0:
        return f'|{" " * length}| 0.0%'
    pct = min(elapsed / total, 1.0)
    bar_len = int(length * pct)
    bar = fill * bar_len + ' ' * (length - bar_len)
    return f'|{bar}| {pct * 100:.1f}%'


PREFIX = "  |"


def print_course_tree(course_name, course_per, units_data, sco_fetcher):
    """打印课程目录树。sco_fetcher(unit_index) 返回该单元的 SCO 列表"""
    try:
        term_cols = os.get_terminal_size().columns - 1
    except Exception:
        term_cols = 79
    print()
    print(PREFIX)
    print(f"{PREFIX}__{course_name} ({course_per}%)"[:term_cols])
    for i, unit in enumerate(units_data):
        visible = unit.get('visible') == 'true'
        status = '' if visible else ' [未开放]'
        print(PREFIX)
        print(f"{PREFIX}{PREFIX}"[:term_cols])
        print(f"{PREFIX}{PREFIX}__{unit['unitname']}{status}"[:term_cols])
        if visible:
            try:
                items = sco_fetcher(i)
            except Exception:
                items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                loc = item.get('location', item.get('id', ''))
                done = ' [已完成]' if item.get('iscomplete') == '已完成' else ''
                print(f"{PREFIX}{PREFIX}{PREFIX}__{loc}{done}"[:term_cols])


# ============================================================
# 密码加密 (复刻自SSO前端 generateCipherText)
# ============================================================
def generate_cipher_text(password):
    """模拟前端的 generateCipherText 函数"""
    T0 = int(time.time() * 1000)  # Date.now()
    P = password.encode('utf-8')
    V = (T0 >> 16) & 0xFF
    for byte in P:
        V ^= byte
    remainder = V % 100
    T1 = (T0 // 100) * 100 + remainder
    P1 = ''.join(f'{b:02x}' for b in P)
    S = f'{T1}*{P1}'
    E = base64.b64encode(S.encode('utf-8')).decode('utf-8')
    return E, T1


# ============================================================
# 登录 SSO (新OIDC系统)
# ============================================================
def sso_login(username, password):
    """通过SSO登录获取welearn cookies"""
    from urllib.parse import unquote, parse_qs, urlparse

    sso = Session()
    sso.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    # Step 1: 获取OIDC授权URL
    prelogin_url = 'https://welearn.sflep.com/user/prelogin.aspx?loginret=http%3a%2f%2fwelearn.sflep.com%2fuser%2floginredirect.aspx'
    resp = sso.get(prelogin_url, allow_redirects=False)
    if 'Location' not in resp.headers:
        print('获取登录地址失败!!')
        return None

    authorize_url = resp.headers['Location']

    # Step 2: 访问授权URL，跟随跳转到transfer.html
    resp2 = sso.get(authorize_url, allow_redirects=True)

    # 从transfer.html的URL中提取returnUrl作为rturl
    parsed = urlparse(resp2.url)
    url_params = parse_qs(parsed.query)
    rturl = unquote(url_params.get('returnUrl', [''])[0])
    if not rturl:
        print('获取登录参数失败!!')
        return None

    # Step 3: 加密密码并提交登录
    pwd_enc, ts = generate_cipher_text(password)
    login_data = {
        'account': username,
        'pwd': pwd_enc,
        'ts': ts,
        'rturl': rturl,
    }

    login_headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://sso.sflep.com',
        'Referer': 'https://sso.sflep.com/idsvr/login.html',
    }

    login_resp = sso.post(
        'https://sso.sflep.com/idsvr/account/login',
        data=login_data,
        headers=login_headers,
    )

    try:
        result = login_resp.json()
    except Exception:
        print(f'登录响应异常: {login_resp.text[:200]}')
        return None

    if result.get('code') == 0:
        redirect_url = result.get('data', '')
        if redirect_url:
            # 返回的是相对路径，需要添加基础URL
            if redirect_url.startswith('/'):
                redirect_url = 'https://sso.sflep.com/idsvr' + redirect_url
            # 跟随OIDC回调完成认证
            final_resp = sso.get(redirect_url, allow_redirects=True)
        print('登录成功!!')
        return sso.cookies
    else:
        msg = result.get('msg', result.get('message', '未知错误'))
        print(f'登录失败!! {msg}')

        # 检查是否需要验证码
        extra = result.get('extraCheck', {})
        if extra.get('vcToken'):
            print('需要短信验证码验证')
        if 'captcha' in str(result).lower() or '验证码' in str(result):
            print('需要图片验证码（连续失败次数过多）')

        return None


# ============================================================
# 多线程刷课
# ============================================================
class NewThread(Thread):
    def __init__(self, learntime, x):
        super().__init__(daemon=True)
        self.learntime = learntime
        self.x = x

    def run(self):
        startstudy(self.learntime, self.x)


class TimeThread(Thread):
    def __init__(self, task_idx, statuses, target_time, x):
        super().__init__(daemon=True)
        self.task_idx = task_idx
        self.statuses = statuses
        self.target_time = target_time
        self.x = x

    def run(self):
        startstudy_time(self.task_idx, self.statuses, self.target_time, self.x)


# ============================================================
# 核心刷课函数
# ============================================================
def startstudy(learntime, x):
    global way1Succeed, way2Succeed, way1Failed, way2Failed

    # 每个任务用独立session，避免状态污染
    s = Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    s.cookies.update(session.cookies)

    scoid = x['id']
    url = f'https://welearn.sflep.com/Ajax/SCO.aspx?uid={uid}'
    referrer = 'https://welearn.sflep.com/student/StudyCourse.aspx'

    # CMI数据模板
    cmi_data = json.dumps({
        "cmi": {
            "completion_status": "completed",
            "interactions": [],
            "launch_data": "",
            "progress_measure": "1",
            "score": {"scaled": str(learntime), "raw": "100"},
            "session_time": "0",
            "success_status": "unknown",
            "total_time": "0",
            "mode": "normal"
        },
        "adl": {"data": []},
        "cci": {
            "data": [],
            "service": {
                "dictionary": {"headword": "", "short_cuts": ""},
                "new_words": [], "notes": [], "writing_marking": [],
                "record": {"files": []},
                "play": {"offline_media_id": "9999"}
            },
            "retry_count": "0",
            "submit_time": ""
        }
    })

    # 开始学习
    back = s.post(url, data={
        'action': 'startsco160928',
        'uid': uid, 'cid': cid, 'scoid': scoid,
        'classid': classid, 'tid': '-1'
    }, headers={'Referer': referrer})

    location = x.get("location", scoid)
    print(f'开始学习: {location}')

    # 设置CMI数据
    s.post(url, data={
        'action': 'setscoinfo',
        'cid': cid, 'scoid': scoid, 'uid': uid,
        'data': cmi_data,
        'isend': 'False'
    }, headers={'Referer': referrer})

    # 提交学习结果
    req = s.post(url, data={
        'action': 'savescoinfo160928',
        'cid': cid, 'scoid': scoid, 'uid': uid,
        'progress': '100', 'crate': str(learntime),
        'status': 'unknown', 'cstatus': 'completed', 'trycount': '0'
    }, headers={'Referer': referrer})

    print(f'>>>>>>>>>>>>>>正确率: {learntime}%')

    if '"ret":0' in req.text:
        print('提交成功!!!')
        way1Succeed.append(0)
    else:
        print('提交失败!!!')
        way1Failed.append(0)

    # 方式2: 100%正确率
    req = s.post(url, data={
        'action': 'savescoinfo160928',
        'cid': cid, 'scoid': scoid, 'uid': uid,
        'progress': '100', 'crate': '100',
        'status': 'unknown', 'cstatus': 'completed', 'trycount': '0'
    }, headers={'Referer': referrer})

    if '"ret":0' in req.text:
        print('方式2:成功!!!')
        way2Succeed.append(0)
    else:
        print('方式2:失败!!!')
        way2Failed.append(0)

    print(f'[ 已完成 ]    {location}')


# ============================================================
# 核心刷时长函数（多线程版）
# ============================================================
def startstudy_time(task_idx, statuses, target_time, x):
    """刷时长模式：每个线程独立session，通过keepsco累积时间"""
    global way1Succeed, way2Succeed, way1Failed, way2Failed

    scoid = x['id']
    url = f'https://welearn.sflep.com/Ajax/SCO.aspx?uid={uid}'
    referrer = 'https://welearn.sflep.com/student/StudyCourse.aspx'

    # 每个线程独立session
    ts = Session()
    ts.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    ts.cookies.update(session.cookies)

    # 开始学习
    try:
        back = ts.post(url, data={
            'action': 'startsco160928',
            'uid': uid, 'cid': cid, 'scoid': scoid,
            'classid': classid, 'tid': '-1'
        }, headers={'Referer': referrer})
        if back.json().get('ret', -1) != 0:
            statuses[task_idx]['status'] = '失败'
            way1Failed.append(0)
            return
    except Exception:
        statuses[task_idx]['status'] = '异常'
        way1Failed.append(0)
        return

    # keepsco循环累积时间
    elapsed = 0
    session_time = 0
    total_time = '0'
    statuses[task_idx]['status'] = '刷取中'

    while elapsed < target_time:
        try:
            resp = ts.post(url, data={
                'action': 'keepsco_with_getticket_with_updatecmitime',
                'uid': uid, 'cid': cid, 'scoid': scoid,
                'session_time': str(session_time),
                'total_time': str(total_time),
                'timelimitsec': '0', 'endcaltime': 'false'
            }, headers={'Referer': referrer})

            kd = resp.json()
            if kd.get('ret', -1) not in (0, 1):
                break

            elapsed += 1
            session_time += 1
            total_time = str(int(total_time) + 1) if total_time.isdigit() else str(elapsed)
            statuses[task_idx]['elapsed'] = elapsed
            time.sleep(1)
        except Exception:
            time.sleep(2)
            break

    # 设置CMI数据
    cmi_data = json.dumps({
        "cmi": {
            "completion_status": "completed",
            "interactions": [],
            "launch_data": "",
            "progress_measure": "1",
            "score": {"scaled": "100", "raw": "100"},
            "session_time": str(session_time),
            "success_status": "unknown",
            "total_time": str(total_time),
            "mode": "normal"
        },
        "adl": {"data": []},
        "cci": {
            "data": [],
            "service": {
                "dictionary": {"headword": "", "short_cuts": ""},
                "new_words": [], "notes": [], "writing_marking": [],
                "record": {"files": []},
                "play": {"offline_media_id": "9999"}
            },
            "retry_count": "0",
            "submit_time": ""
        }
    })

    ts.post(url, data={
        'action': 'setscoinfo',
        'cid': cid, 'scoid': scoid, 'uid': uid,
        'data': cmi_data,
        'isend': 'False'
    }, headers={'Referer': referrer})

    req = ts.post(url, data={
        'action': 'savescoinfo160928',
        'cid': cid, 'scoid': scoid, 'uid': uid,
        'progress': '100', 'crate': '100',
        'status': 'unknown', 'cstatus': 'completed', 'trycount': '0'
    }, headers={'Referer': referrer})

    if '"ret":0' in req.text:
        statuses[task_idx]['status'] = '已完成'
        way1Succeed.append(0)
    else:
        statuses[task_idx]['status'] = '失败'
        way1Failed.append(0)


# ============================================================
# 登录流程
# ============================================================
def auto_login(banner_version):
    """自动登录: 配置文件凭据 → 交互式"""
    global session

    config = load_welearn_config()

    # Step 1: 尝试配置文件账号密码自动登录
    username = config.get("username", "").strip()
    password = config.get("password", "").strip()
    if username and password:
        cookies = try_auto_login(username, password)
        if cookies:
            session.cookies.update(cookies)
            save_welearn_cookies()
            print("[auto] cookies已保存")
            return True

    # Step 2: 兜底交互式登录
    if not do_login(banner_version):
        return False

    save_welearn_cookies()
    return True


def do_login(banner_version):
    global session
    username = input('请输入账号: ')
    password = input('请输入密码: ')
    printline()

    cookies = sso_login(username, password)
    if cookies:
        session.cookies.update(cookies)
        _save_welearn_credentials(username, password)
        return True
    return False


def login_time():
    return auto_login('welearn时长版')


def login_course():
    return auto_login('welearn课程版')


# ============================================================
# 主程序入口
# ============================================================
if __name__ == '__main__':
    print('**********  WeLearn 刷课工具  **********')

    # 先登录，再选模式
    if not auto_login('welearn'):
        input('登录失败，按任意键退出...')
        exit()

    while True:
        os.system('cls')
        mode = input('请选择Welearn刷课模式: \n   1.Welearn课程刷取\n   2.Welearn时长刷取\n\n请输入数字1或2: ')

        os.system('cls')

        if mode not in ('1', '2'):
            print('输入无效，请重新选择！')
            input('按任意键继续...')
            continue

        # ========== 查询课程 ==========
        url = 'https://welearn.sflep.com/ajax/authCourse.aspx?action=gmc'
        headers = {'Referer': 'https://welearn.sflep.com/student/index.aspx'}
        response = session.get(url, headers=headers)
        text = response.text

        if '"clist":[]' in text:
            print('发生错误!!!可能是登录错误或没有课程!!!')
            input('按任意键退出...')
            exit()
        else:
            print('查询课程成功!!!')

        # 解析课程列表
        index_list = json.loads(text)['clist']
        print('我的课程: \n')
        for i, course in enumerate(index_list):
            per = course.get('per', 0)
            if mode == '2':
                print(f'[id:{i + 1:>2d}]  完成度 {per:>2d}%  {course["name"]}')
            else:
                print(f'[NO.{i + 1:>2d}]  完成度 {per:>2d}%  {course["name"]}')

        # 选择课程（输入0返回上一级）
        while True:
            if mode == '2':
                order_str = input('\n请输入需要刷时长的课程id（id为上方[]内的序号，输入0返回上一级）: ')
            else:
                order_str = input('\n请输入你要完成的课程编号(上方[]内的数字，输入0返回上一级): ')
            if order_str == '0':
                break
            try:
                order = int(order_str)
                cid = index_list[order - 1]['cid']
            except (ValueError, IndexError):
                print('输入无效，请重新输入！')
                continue
            break

        if order_str == '0':
            continue

        print('获取单元中...')

        # 获取课程详情（带重试）
        course_url = f'https://welearn.sflep.com/student/course_info.aspx?cid={cid}'
        for retry in range(3):
            try:
                response = session.get(course_url, headers=headers, timeout=15)
                text = response.text
                break
            except Exception as e:
                if retry < 2:
                    print(f'网络异常，正在重试({retry+1}/3)...')
                    time.sleep(2)
                else:
                    print(f'获取课程详情失败: {e}')
                    input('按任意键返回重新选择课程...')
                    continue
        else:
            continue

        uid_match = re.search(r'"uid":(.*?),', text)
        classid_match = re.search(r'"classid":"(.*?)"', text)
        if uid_match:
            uid = uid_match.group(1)
        if classid_match:
            classid = classid_match.group(1)

        # 获取单元信息（带重试）
        url = 'https://welearn.sflep.com/ajax/StudyStat.aspx'
        for retry in range(3):
            try:
                response = session.post(url, data={
                    'action': 'courseunits',
                    'cid': cid, 'uid': uid
                }, headers={'Referer': course_url}, timeout=15)
                break
            except Exception as e:
                if retry < 2:
                    print(f'网络异常，正在重试({retry+1}/3)...')
                    time.sleep(2)
                else:
                    print(f'获取单元信息失败: {e}')
                    input('按任意键返回重新选择课程...')
                    continue
        else:
            continue

        info = response.json()

        # 加载 tree_view 配置
        welearn_config = load_welearn_config()
        tree_view = welearn_config.get("tree_view", True)

        # SCO 缓存 (unit_index -> items)，树形打印时填充，后续构建 task_list 复用
        sco_cache = {}

        def fetch_sco(unit_idx):
            if unit_idx not in sco_cache:
                sco_url = f'https://welearn.sflep.com/ajax/StudyStat.aspx?action=scoLeaves&cid={cid}&uid={uid}&unitidx={unit_idx}&classid={classid}'
                resp = session.get(sco_url, headers={'Referer': course_url})
                try:
                    sco_cache[unit_idx] = resp.json().get('info', [])
                except Exception:
                    sco_cache[unit_idx] = []
            return sco_cache[unit_idx]

        if tree_view:
            course_name = index_list[order - 1]['name']
            course_per = index_list[order - 1].get('per', 0)
            print_course_tree(course_name, course_per, info.get('info', []), fetch_sco)

        # 显示单元列表并选择（输入b返回上一级）
        while True:
            if mode == '2':
                print('\n[id: 0]  按顺序刷全部单元学习时长')
                for i, unit in enumerate(info.get('info', [])):
                    if unit.get('visible') == 'true':
                        print(f'[id:{i + 1:>2d}]  [已开放]  {unit["unitname"]}')
                    else:
                        print(f'[id:{i + 1:>2d}]  ![未开放]! {unit["unitname"]}')
                unitsnum = input('\n\n请选择要刷时长的单元id（id为上方[]内的序号，输入0为刷全部单元，若多选用逗号隔开，如 1,3,5，输入b返回上一级）： ')
            else:
                print('[NO. 0]  按顺序完成全部单元课程')
                for i, unit in enumerate(info.get('info', [])):
                    if unit.get('visible') == 'true':
                        print(f'[NO.{i + 1:>2d}]  [已开放]  {unit["unitname"]}')
                    else:
                        print(f'[NO.{i + 1:>2d}]  ![未开放]! {unit["unitname"]}')
                unitsnum = input('\n\n请选择需要完成的单元序号（上方[]内的数字，输入0为按顺序刷全部单元，若多选用逗号隔开，如 1,3,5，输入b返回上一级）： ')

            if unitsnum == 'b':
                break

            if unitsnum == '0':
                index_list2 = list(range(len(info.get('info', []))))
            else:
                try:
                    index_list2 = [int(x.strip()) - 1 for x in unitsnum.split(',')]
                except ValueError:
                    print('输入无效，请重新输入！')
                    continue

            # 设置学习参数（输入b返回上一级）
            while True:
                if mode == '2':
                    inputtime = input(
                        '\n\n模式1:每个练习增加指定学习时长，请直接输入时间\n'
                        '如:希望每个练习增加30秒，则输入 30\n\n'
                        '模式2:每个练习增加随机时长，请输入时间上下限并用英文逗号隔开\n'
                        '如:希望每个练习增加10～30秒，则输入 10,30\n\n'
                        '请严格按照以上格式输入（逗号必须为英文逗号，输入b返回上一级）: '
                    )
                    if inputtime == 'b':
                        break
                    if ',' in inputtime:
                        parts = [p.strip() for p in inputtime.split(',')]
                        mytime = [int(p) for p in parts if p.isdigit()]
                        randommode_time = True
                    else:
                        if inputtime.isdigit():
                            mytime = int(inputtime)
                            randommode_time = False
                        else:
                            print('输入无效，请重新输入！')
                            continue
                else:
                    inputcrate = input(
                        '模式1:每个练习指定正确率，请直接输入指定的正确率\n'
                        '如:希望每个练习正确率均为100，则输入 100\n\n'
                        '模式2:每个练习随机正确率，请输入正确率上下限并用英文逗号隔开\n'
                        '如:希望每个练习正确率为70～100，则输入 70,100\n\n'
                        '请严格按照以上格式输入每个练习的正确率（逗号必须为英文逗号，输入b返回上一级）: '
                    )
                    if inputcrate == 'b':
                        break
                    if ',' in inputcrate:
                        parts = [p.strip() for p in inputcrate.split(',')]
                        if all(p.isdigit() for p in parts):
                            mycrate = [int(p) for p in parts]
                        else:
                            mycrate = [int(p) for p in parts if p.isdigit()]
                        randommode = True
                    else:
                        if inputcrate.isdigit():
                            mycrate = int(inputcrate)
                            randommode = False
                        else:
                            print('输入无效，请重新输入！')
                            continue

                # 输入正确，进入主循环
                break  # 跳出时间/正确率输入循环

            if mode == '2' and inputtime == 'b':
                continue  # 返回单元选择
            if mode == '1' and inputcrate == 'b':
                continue  # 返回单元选择

            break  # 跳出单元选择循环，进入主循环

        if unitsnum == 'b':
            continue  # 返回课程选择

        # ========== 使用scoLeaves API获取项目列表 ==========
        all_units = info.get('info', [])
        sco_leaves_url = 'https://welearn.sflep.com/ajax/StudyStat.aspx'
        sco_leaves_headers = {'Referer': course_url}

        # ========== 收集所有待处理项目 ==========
        task_list = []
        skip_count = 0
        for j in index_list2:
            if j >= len(all_units):
                print(f'[!!跳过!!]    单元{j+1}不存在')
                continue

            unit = all_units[j]
            unitname = unit.get('unitname', f'单元{j+1}')

            # 通过scoLeaves获取该单元的所有项目（优先使用缓存）
            if j in sco_cache:
                items = sco_cache[j]
            else:
                resp = session.get(
                    f'{sco_leaves_url}?action=scoLeaves&cid={cid}&uid={uid}&unitidx={j}&classid={classid}',
                    headers=sco_leaves_headers
                )
                try:
                    sco_data = resp.json()
                    items = sco_data.get('info', [])
                except Exception:
                    print(f'[!!跳过!!]    {unitname} (数据异常)')
                    continue

            if not items:
                print(f'[!!跳过!!]    {unitname} (无项目)')
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                # if item.get('isvisible') != 'true':
                #     skip_count += 1
                #     continue
                # if mode == '1' and item.get('iscomplete') == '已完成':
                #     skip_count += 1
                #     continue

                scoid = item['id']
                location = item.get('location', scoid)

                if mode == '2':
                    if randommode_time:
                        learntime = random.randint(min(mytime), max(mytime)) if len(mytime) > 1 else mytime[0]
                    else:
                        learntime = mytime
                else:
                    if randommode:
                        if len(mycrate) > 1:
                            lo, hi = min(mycrate), max(mycrate)
                            learntime = int(round(random.gauss((lo + hi) / 2, (hi - lo) / 6)))
                            learntime = max(lo, min(hi, learntime))
                        else:
                            learntime = mycrate[0]
                    else:
                        learntime = mycrate

                task_list.append({'id': scoid, 'location': location, 'learntime': learntime})

        if not task_list:
            print('没有需要处理的项目!')
            input('按任意键退出...')
            break

        # ========== 刷时长模式：多线程并发，主循环定时刷新显示 ==========
        if mode == '2':
            welearn_config = load_welearn_config()
            progressbar_view = welearn_config.get("progressbar_view", True)
            N = len(task_list)
            max_loc_len = max(len(t['location']) for t in task_list)

            # 共享状态：每个线程更新自己的条目
            statuses = [
                {'status': '等待中', 'elapsed': 0, 'target': t['learntime']}
                for t in task_list
            ]

            def redraw():
                for i in range(N):
                    loc = task_list[i]['location']
                    pad = ' ' * (max_loc_len - len(loc))
                    s = statuses[i]
                    st = s['status']
                    if st == '刷取中':
                        if progressbar_view:
                            bar = progress_bar(s['elapsed'], s['target'])
                            line = f'  [{i+1:>3d}/{N}]  {loc}{pad}  {bar} ({s["elapsed"]}/{s["target"]}秒)'
                        else:
                            line = f'  [{i+1:>3d}/{N}]  {loc}{pad}  {s["elapsed"]:>4d}/{s["target"]}秒'
                    elif st == '已完成':
                        line = f'  [{i+1:>3d}/{N}]  {loc}{pad}  已完成'
                    elif st == '失败':
                        line = f'  [{i+1:>3d}/{N}]  {loc}{pad}  失败'
                    elif st == '异常':
                        line = f'  [{i+1:>3d}/{N}]  {loc}{pad}  异常'
                    else:
                        line = f'  [{i+1:>3d}/{N}]  {loc}{pad}  等待中'
                    print(f'\r\033[K{line}')

            # 启动所有线程
            print(f'\n共 {N} 个待刷时长项目 (跳过 {skip_count} 个)\n')
            threads = []
            for i, task in enumerate(task_list):
                t = TimeThread(i, statuses, task['learntime'],
                               {'id': task['id'], 'location': task['location']})
                t.start()
                threads.append(t)

            # 主循环：定时刷新显示，直到所有线程完成
            while any(t.is_alive() for t in threads):
                print(f'\r\033[{N}A')
                redraw()
                time.sleep(1)

            # 最终显示
            print(f'\r\033[{N}A')
            redraw()

            total_success = len(way1Succeed) + len(way2Succeed)
            total_failed = len(way1Failed) + len(way2Failed)
            print(f'全部完成!!\n')
            print(f'总计: {total_success} 成功, {total_failed} 失败')
            print('按任意键退出...')
            input()
            break

        # ========== 刷课程模式：多线程处理 ==========
        threads = []
        for task in task_list:
            t = NewThread(task['learntime'], {'id': task['id'], 'location': task['location']})
            t.start()
            threads.append(t)

        print(f'\n已启动 {len(threads)} 个任务，等待完成中...')
        for t in threads:
            t.join()

        total_success = len(way1Succeed) + len(way2Succeed)
        total_failed = len(way1Failed) + len(way2Failed)
        print(f'\n\n        ****************************************************************')
        print(f'全部完成!!\n')
        print(f'总计: {total_success} 成功, {total_failed} 失败')
        print(f'(方式1: {len(way1Succeed)} 成功, {len(way1Failed)} 失败)')
        print(f'(方式2: {len(way2Succeed)} 成功, {len(way2Failed)} 失败)')
        print('按任意键退出...')
        input()
        break  # 退出外层while True
