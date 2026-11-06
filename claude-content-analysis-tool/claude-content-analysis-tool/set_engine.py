#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""翻译引擎固定为 Google。此脚本保留做兼容：python set_engine.py google"""
import sys

import config_lib as cl

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    name = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if name and name != "google":
        print(f"引擎只保留 google（已删除 claude / local），忽略：{name}")
    cfg = cl.read_config()
    cfg["engine"] = "google"
    cl.write_config(cfg)
    print("引擎 = google（已固定）")


if __name__ == "__main__":
    main()
