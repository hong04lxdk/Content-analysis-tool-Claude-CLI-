#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude content analysis tool 配置命令行。

用法：
  python config.py show                          查看当前配置
  python config.py llm <claude|local>            解释服务用哪个 LLM
  python config.py commonlang <zh-CN|en|...>     常用语言
  python config.py lang <zh-CN|en|...>           目标语言
  python config.py explain <on|off>              解释服务开关
  python config.py translate <on|off>            翻译服务开关
  python config.py popup <秒数>                   弹窗自动关闭秒数
  python config.py fontsize <字号>                译文字号（默认 14，范围 8~40）
  python config.py minlen <字数>                  少于该字数不翻译
  python config.py maxlen <字数>                  超过则截断
  python config.py model <模型名>                 Claude 模型
  python config.py localmodel <模型名>            本地模型
  python config.py set <点分键> <值>               通用：如 set llms.local.model qwen
  python config.py get <点分键>                   通用读取

翻译引擎固定为 Google；常用语言 ↔ 目标语言双向互译，其它语言不翻译。
改完写 cache + 源目录两份，即时生效（无需重启）。
"""
import sys
import config_lib as cl

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _err(msg):
    print("错误：" + msg)
    print(__doc__)
    sys.exit(1)


def _coerce(v):
    s = str(v).strip()
    for ctor in (int, float):
        try:
            return ctor(s)
        except ValueError:
            pass
    return s


def _apply(cfg):
    targets = cl.write_config(cfg)
    print(f"已写入 {len(targets)} 处，即时生效：")
    for p in targets:
        print("  - " + p)


def _onoff(v):
    x = str(v).strip().lower()
    if x in ("on", "1", "true", "yes", "开"):
        return True
    if x in ("off", "0", "false", "no", "关"):
        return False
    _err("用法：on / off")


def cmd_show():
    cfg = cl.read_config()
    targets = cl.find_targets()
    if targets:
        print("生效副本（cache）：" + targets[0])
    print("  llm              = " + str(cfg["llm"]))
    print("  common_lang      = " + str(cfg["common_lang"]))
    print("  target_lang      = " + str(cfg["target_lang"]))
    print("  engine           = " + str(cfg["engine"]) + "（固定）")
    print("  service_explain  = " + ("on" if cfg["service_explain"] else "off"))
    print("  service_translate= " + ("on" if cfg["service_translate"] else "off"))
    print("  popup_seconds    = " + str(cfg["popup_seconds"]))
    print("  font_size        = " + str(cfg.get("font_size", 14)))
    print("  min_len          = " + str(cfg["min_len"]))
    print("  max_len          = " + str(cfg["max_len"]))
    print("  llms.claude.model= " + str(cfg["llms"]["claude"]["model"]))
    print("  llms.local.model = " + str(cfg["llms"]["local"]["model"]))
    if len(targets) > 1:
        print("  同步副本（%d 处）：" % len(targets))
        for p in targets:
            print("    - " + p)


def main(argv):
    if not argv or argv[0] in ("show", "status"):
        cmd_show()
        return
    cmd, rest = argv[0], argv[1:]

    if cmd == "llm":
        if not rest or rest[0] not in cl.LLM_CHOICES:
            _err("用法：config.py llm <" + "/".join(cl.LLM_CHOICES) + ">")
        cfg = cl.read_config(); cfg["llm"] = rest[0]; _apply(cfg)
    elif cmd == "commonlang":
        if not rest or rest[0] not in cl.LANG_NAMES:
            _err("用法：config.py commonlang <" + "/".join(cl.LANG_NAMES) + ">")
        cfg = cl.read_config(); cfg["common_lang"] = rest[0]; _apply(cfg)
    elif cmd == "lang":
        if not rest or rest[0] not in cl.LANG_NAMES:
            _err("用法：config.py lang <" + "/".join(cl.LANG_NAMES) + ">")
        cfg = cl.read_config(); cfg["target_lang"] = rest[0]; _apply(cfg)
    elif cmd == "explain":
        if not rest:
            _err("用法：config.py explain <on|off>")
        cfg = cl.read_config(); cfg["service_explain"] = _onoff(rest[0]); _apply(cfg)
    elif cmd == "translate":
        if not rest:
            _err("用法：config.py translate <on|off>")
        cfg = cl.read_config(); cfg["service_translate"] = _onoff(rest[0]); _apply(cfg)
    elif cmd == "engine":
        if not rest or rest[0] not in cl.ENGINE_CHOICES:
            _err("引擎只保留 google")
        cfg = cl.read_config(); cfg["engine"] = "google"; _apply(cfg)
    elif cmd == "popup":
        if not rest:
            _err("用法：config.py popup <秒数>")
        cfg = cl.read_config(); cfg["popup_seconds"] = _coerce(rest[0]); _apply(cfg)
    elif cmd == "minlen":
        if not rest:
            _err("用法：config.py minlen <字数>")
        cfg = cl.read_config(); cfg["min_len"] = _coerce(rest[0]); _apply(cfg)
    elif cmd == "maxlen":
        if not rest:
            _err("用法：config.py maxlen <字数>")
        cfg = cl.read_config(); cfg["max_len"] = _coerce(rest[0]); _apply(cfg)
    elif cmd == "model":
        if not rest:
            _err("用法：config.py model <模型名>")
        cfg = cl.read_config(); cfg["llms"]["claude"]["model"] = rest[0]; _apply(cfg)
    elif cmd == "localmodel":
        if not rest:
            _err("用法：config.py localmodel <模型名>")
        cfg = cl.read_config(); cfg["llms"]["local"]["model"] = rest[0]; _apply(cfg)
    elif cmd == "fontsize":
        if not rest:
            _err("用法：config.py fontsize <字号>")
        cfg = cl.read_config(); cfg["font_size"] = _coerce(rest[0]); _apply(cfg)
    elif cmd == "set":
        if len(rest) < 2:
            _err("用法：config.py set <点分键> <值>")
        cfg = cl.read_config()
        try:
            cl.set_path(cfg, rest[0], _coerce(rest[1]))
        except Exception as e:
            _err(f"set 失败：{e}")
        _apply(cfg)
    elif cmd == "get":
        if not rest:
            _err("用法：config.py get <点分键>")
        cfg = cl.read_config()
        try:
            print(cl.get_path(cfg, rest[0]))
        except Exception as e:
            _err(f"get 失败：{e}")
    else:
        _err("未知命令：" + cmd)


if __name__ == "__main__":
    main(sys.argv[1:])
