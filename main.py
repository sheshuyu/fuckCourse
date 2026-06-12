"""fuckCourse v2.0.0 — unified launcher for three independent course tools."""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
CHAOXING_DIR = os.path.join(ROOT, "chaoxing")
ZHS_DIR = os.path.join(ROOT, "zhs")
WELEARN_DIR = os.path.join(ROOT, "welearn")
COOKIES_FILE = os.path.join(ROOT, "cookies.json")
CONFIG_FILE = os.path.join(ROOT, "config.json")


def _python_exe():
    if "CONDA_PREFIX" in os.environ:
        return sys.executable
    conda_python = r"D:\CondaEnvs\fuckcourse\python.exe"
    if os.path.isfile(conda_python):
        return conda_python
    return sys.executable


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def _run(cwd, script_args, name):
    python = _python_exe()
    env = os.environ.copy()
    env["FUCKCOURSE_CONFIG"] = CONFIG_FILE
    env["FUCKCOURSE_COOKIES"] = COOKIES_FILE
    print(f"\n  Starting {name}...\n")
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
            print(f"\n  [{name}] exited with code {result.returncode}")
        input("\n  按任意键返回菜单...")
    except KeyboardInterrupt:
        print(f"\n  [{name}] interrupted by user")
        input("\n  按任意键返回菜单...")
    except Exception as e:
        print(f"\n  [{name}] error: {e}")
        input("\n  按任意键返回菜单...")


def run_chaoxing():
    _run(CHAOXING_DIR, ["main.py"], "chaoxing")


def run_zhs():
    _run(ZHS_DIR, ["main.py"], "zhs")


def run_welearn():
    _run(WELEARN_DIR, ["welearn_decompiled.py"], "welearn")


def print_banner():
    print("=" * 50)
    print("  fuckCourse v2.0.0")
    print("=" * 50)
    print()


def main():
    while True:
        clear()
        print_banner()
        print("  [1] 超星学习通 (Chaoxing)")
        print("  [2] WE Learn (SFLEP)")
        print("  [3] 智慧树 (ZHS)")
        print("  [0] 退出")
        print()
        choice = input("  请选择平台 (0-3): ").strip()

        if choice == "1":
            clear()
            run_chaoxing()
        elif choice == "2":
            clear()
            run_welearn()
        elif choice == "3":
            clear()
            run_zhs()
        elif choice == "0":
            print("\n  再见!")
            break
        else:
            print("  输入无效，请重新选择")
            input("  按任意键继续...")


if __name__ == "__main__":
    main()
