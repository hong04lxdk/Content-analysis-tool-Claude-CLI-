#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""幂等拉起 claude-content-analysis-tool 后台进程（已运行则跳过）。"""
import os
import sys
import ctypes
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
PID_PATH = os.path.join(BASE, "run", "translate.pid")

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def pid_alive(pid):
    if not pid:
        return False
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if h:
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    return False


def find_main_exe():
    """主程序打包成的 exe：优先插件目录，其次桌面。"""
    for p in (os.path.join(BASE, "ContentAnalysisTool.exe"),
              os.path.expanduser("~/Desktop/ContentAnalysisTool.exe")):
        if os.path.exists(p):
            return p
    return None


def main():
    if os.path.exists(PID_PATH):
        try:
            pid = int(open(PID_PATH).read().strip())
            if pid_alive(pid):
                print(f"already running (pid {pid})")
                return
        except Exception:
            pass

    os.makedirs(os.path.dirname(PID_PATH), exist_ok=True)

    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    # 关键：stdout/stderr/stdin 全 DEVNULL + close_fds，避免继承 hook 的 stdout 管道
    exe = find_main_exe()
    if exe:
        subprocess.Popen(
            [exe], cwd=os.path.dirname(exe), creationflags=flags,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        print("started ContentAnalysisTool.exe")
        return

    # 没打包 exe 时退回源码运行
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
        flags |= 0x08000000  # CREATE_NO_WINDOW

    subprocess.Popen(
        [pythonw, os.path.join(BASE, "translate_tool.py")],
        cwd=BASE, creationflags=flags,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    print("started claude-content-analysis-tool (python)")


if __name__ == "__main__":
    main()
