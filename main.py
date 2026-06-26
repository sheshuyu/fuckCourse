"""fuckCourse v3.1.0-dev — unified launcher for course automation tools."""
import os
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = sys._MEIPASS
    DATA_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = APP_DIR
CHAOXING_DIR = os.path.join(APP_DIR, "chaoxing")
ZHS_DIR = os.path.join(APP_DIR, "zhs")
WELEARN_DIR = os.path.join(APP_DIR, "welearn")
YUKETANG_DIR = os.path.join(APP_DIR, "yuketang")
COOKIES_FILE = os.path.join(DATA_DIR, "cookies.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
LOG_DIR = os.path.join(DATA_DIR, "logs")


def _python_exe():
    if "CONDA_PREFIX" in os.environ:
        return sys.executable
    return sys.executable


def clear():
    print("\033[2J\033[H", end="")


def _setup_env():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.environ["FUCKCOURSE_CONFIG"] = CONFIG_FILE
    os.environ["FUCKCOURSE_COOKIES"] = COOKIES_FILE
    os.environ["FUCKCOURSE_LOG_DIR"] = LOG_DIR


def _run(cwd, script_args, name):
    _setup_env()
    print(f"\n  Starting {name}...\n")

    if getattr(sys, 'frozen', False):
        _run_frozen(cwd, script_args, name)
    else:
        _run_subprocess(cwd, script_args, name)


def _run_frozen(cwd, script_args, name):
    script_path = os.path.join(cwd, script_args[0])
    old_argv = sys.argv
    old_cwd = os.getcwd()
    old_path = list(sys.path)
    try:
        os.chdir(cwd)
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        sys.argv = [script_path] + script_args[1:]
        with open(script_path, "rb") as f:
            code = compile(f.read(), script_path, "exec")
        _ns = {"__name__": "__main__", "__file__": script_path, "exit": sys.exit}
        exec(code, _ns)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print(f"\n[{name}] interrupted by user")
    except Exception as e:
        print(f"\n[{name}] error: {e}")
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
        sys.path[:] = old_path


def _run_subprocess(cwd, script_args, name):
    import subprocess
    python = _python_exe()
    env = os.environ.copy()
    try:
        result = subprocess.run(
            [python] + script_args,
            cwd=cwd,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=env,
        )
        if result.returncode != 0:
            print(f"\n[{name}] exited with code {result.returncode}")
        print()
        input("按任意键返回菜单...")
    except KeyboardInterrupt:
        print(f"\n[{name}] interrupted by user")
        print()
        input("按任意键返回菜单...")
    except Exception as e:
        print(f"\n[{name}] error: {e}")
        print()
        input("按任意键返回菜单...")


def run_chaoxing():
    _run(CHAOXING_DIR, ["main.py"], "chaoxing")


def run_zhs():
    _run(ZHS_DIR, ["main.py"], "zhs")


def run_welearn():
    _run(WELEARN_DIR, ["welearn_decompiled.py"], "welearn")


def run_yuketang():
    _run(YUKETANG_DIR, ["main.py"], "yuketang")


def print_banner():
    print("=" * 50)
    print("             fuckCourse v3.1.0-dev")
    print("             designed by snake")
    print("=" * 50)
    print()


def main():
    while True:
        clear()
        print_banner()
        print("  [1] 超星学习通 (Chaoxing)")
        print("  [2] WE Learn (SFLEP)")
        print("  [3] 智慧树 (ZHS)")
        print("  [4] 雨课堂 (Yuketang)")
        print("  [0] 退出")
        print()
        choice = input("  请选择平台 (0-4): ").strip()

        if choice == "1":
            clear()
            run_chaoxing()
        elif choice == "2":
            clear()
            run_welearn()
        elif choice == "3":
            clear()
            run_zhs()
        elif choice == "4":
            clear()
            run_yuketang()
        elif choice == "0":
            print("\n再见!")
            break
        else:
            print("输入无效，请重新选择")
            input("按任意键继续...")


if __name__ == "__main__":
    main()
