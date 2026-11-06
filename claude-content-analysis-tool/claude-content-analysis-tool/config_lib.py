#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude content analysis tool 配置读写（CLI / GUI / 主程序共用）。

定位两处 config.json 并保持一致：
  1) cache 运行副本（~/.claude/plugins/cache/.../<版本>/config.json）—— 工具实际读这份；
  2) Desktop 源目录（~Desktop/claude-content-analysis-tool-marketplace/claude-content-analysis-tool/config.json）—— 重装时覆盖。
改配置写两份，即时生效（translate_tool 每次操作前重读，无需重启）。
"""

import os
import sys
import json
import glob

LANG_NAMES = {
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "ru": "Русский",
}

# 翻译引擎：只保留谷歌
ENGINE_CHOICES = ["google"]

# LLM 后端：Claude setting（复用 ~/.claude/settings.json）/ 本地模型（Ollama）
LLM_CHOICES = ["claude", "local"]
LLM_LABELS = {"claude": "Claude setting", "local": "本地模型"}

# 两个服务开关
SERVICE_KEYS = ["service_explain", "service_translate"]

DEFAULTS = {
    "llm": "claude",
    "common_lang": "zh-CN",
    "target_lang": "en",
    "engine": "google",
    "service_explain": True,
    "service_translate": True,
    "popup_seconds": 8,
    "font_size": 14,
    "min_len": 2,
    "max_len": 2000,
    "engines": {"google": {}},
    "llms": {
        "claude": {"model": "", "base_url": "", "auth_token": ""},
        "local": {"model": "qwen2.5:7b", "base_url": "http://localhost:11434"},
    },
}


def _deep_merge(base, override):
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            out[k] = _deep_merge(base[k], v)
        else:
            out[k] = v
    return out


def _migrate(raw):
    """老 schema（engines.claude / engines.local、单目标语言）迁到新 schema。"""
    raw = dict(raw or {})
    engines = dict(raw.get("engines") or {})
    old_claude = engines.pop("claude", None)
    old_local = engines.pop("local", None)
    raw["engines"] = engines
    if "llms" not in raw and (old_claude or old_local):
        raw["llms"] = {
            "claude": old_claude or dict(DEFAULTS["llms"]["claude"]),
            "local": old_local or dict(DEFAULTS["llms"]["local"]),
        }
    if "common_lang" not in raw:
        raw["common_lang"] = DEFAULTS["common_lang"]
    return raw


def _app_dir():
    """程序所在目录：打包成 exe 时是 exe 目录，否则是脚本目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def portable_config_path():
    """便携配置：exe / 脚本同目录的 config.json（解压即用的版本用这个）。"""
    return os.path.join(_app_dir(), "config.json")


def user_config_path():
    """独立运行时没有插件目录可用，就落到用户目录。"""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "ContentAnalysisTool", "config.json")


def find_targets():
    """返回所有应写入的 config.json 路径。

    第一项是「实际生效」的配置：
      1) 插件 cache 运行副本（本机装插件时）
      2) Desktop 源目录 / 脚本同目录
      3) 便携配置（exe 同目录，存在时）
    都没有时返回 [用户目录配置]（首次保存会创建）。
    """
    targets = []
    seen = set()

    def add(p):
        p = os.path.abspath(p)
        if p not in seen and os.path.exists(p):
            seen.add(p)
            targets.append(p)

    # 1) cache 运行副本（版本号高的排前面 = 当前生效）
    cache = sorted(glob.glob(os.path.expanduser(
        "~/.claude/plugins/cache/claude-content-analysis-tool-marketplace/claude-content-analysis-tool/*/config.json")))
    for p in reversed(cache):
        add(p)

    # 2) Desktop 源目录（耐久 / 重装覆盖）
    add(os.path.expanduser("~/Desktop/claude-content-analysis-tool-marketplace/claude-content-analysis-tool/config.json"))

    # 3) 本程序同目录（源码目录，或 exe 同目录的便携配置）
    add(portable_config_path())

    # 4) 都没有：落到用户目录，保证独立版本也能保存设置
    if not targets:
        targets.append(user_config_path())
    return targets


def read_config():
    """读当前生效配置（cache 优先，缺字段回填 DEFAULTS，并做老 schema 迁移）。"""
    raw = {}
    targets = find_targets()
    if targets:
        try:
            with open(targets[0], encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            pass
    cfg = _deep_merge({}, DEFAULTS)
    cfg = _deep_merge(cfg, _migrate(raw))
    cfg["engine"] = "google"  # 引擎只保留谷歌
    return cfg


def write_config(cfg):
    """写所有目标（原子替换：先写 .tmp 再 os.replace）。返回写到的路径列表。"""
    targets = find_targets()
    if not targets:
        raise RuntimeError("找不到 config.json（源目录与 cache 副本都不存在）")
    data = json.dumps(cfg, ensure_ascii=False, indent=2)
    for p in targets:
        d = os.path.dirname(p)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, p)
    return targets


def get_path(cfg, dotted):
    node = cfg
    for k in dotted.split("."):
        node = node[k]
    return node


def set_path(cfg, dotted, value):
    keys = dotted.split(".")
    node = cfg
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = value
