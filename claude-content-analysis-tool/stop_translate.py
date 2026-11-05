#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""停止 claude-content-analysis-tool 后台进程（按 pid 文件终止）。"""
import os
import ctypes

BASE = os.path.dirname(os.path.abspath(__file__))
PID_PATH = os.path.join(BASE, "run", "translate.pid")


def main():
    if not os.path.exists(PID_PATH):
        print("not running")
        return
    try:
        pid = int(open(PID_PATH).read().strip())
    except Exception:
        print("bad pid file")
        return
    PROCESS_TERMINATE = 0x0001
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if h:
        ctypes.windll.kernel32.TerminateProcess(h, 0)
        ctypes.windll.kernel32.CloseHandle(h)
        print(f"stopped pid {pid}")
    else:
        print("process not found")
    try:
        os.remove(PID_PATH)
    except Exception:
        pass


if __name__ == "__main__":
    main()
