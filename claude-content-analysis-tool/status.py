#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看 Claude content analysis tool 状态。"""
import os
import ctypes

import config_lib as cl

BASE = os.path.dirname(os.path.abspath(__file__))
PID = os.path.join(BASE, "run", "translate.pid")

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def pid_alive(pid):
    if not pid:
        return False
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if h:
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    return False


def main():
    cfg = cl.read_config()
    running = False
    if os.path.exists(PID):
        try:
            running = pid_alive(int(open(PID).read().strip()))
        except Exception:
            pass
    print(f"llm={cfg['llm']}  common_lang={cfg['common_lang']}  target_lang={cfg['target_lang']}  "
          f"explain={'on' if cfg['service_explain'] else 'off'}  "
          f"translate={'on' if cfg['service_translate'] else 'off'}  "
          f"running={'yes' if running else 'no'}")


if __name__ == "__main__":
    main()
