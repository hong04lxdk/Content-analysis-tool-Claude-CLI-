#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude content analysis tool 设置面板（嵌在主程序里的「设置」窗口，同一个 exe）。"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

import config_lib as cl

APP_TITLE = "Claude content analysis tool 设置"

# 语言下拉：显示名 -> 代码
LANG_DISPLAY = [(f"{name} ({code})", code) for code, name in cl.LANG_NAMES.items()]
CODE_OF = dict(LANG_DISPLAY)                         # 显示名 -> 代码（apply 存盘用）
DISPLAY_OF = dict((c, d) for d, c in LANG_DISPLAY)   # 代码 -> 显示名（reload 展示用）

# LLM 下拉：显示名 -> 代码
LLM_DISPLAY = [(label, code) for code, label in cl.LLM_LABELS.items()]
LLM_CODE_OF = dict(LLM_DISPLAY)                          # 显示名 -> 代码（apply 存盘用）
LLM_DISPLAY_OF = dict((code, label) for label, code in LLM_DISPLAY)  # 代码 -> 显示名（reload 展示用）


def _settings_model():
    """当前 Claude settings（~/.claude/settings.json）里配置的 model。"""
    p = os.path.expanduser("~/.claude/settings.json")
    try:
        with open(p, encoding="utf-8-sig") as f:
            return (json.load(f).get("model") or "")
    except Exception:
        return ""


class ConfigPanel(ttk.Frame):
    """配置表单。on_applied 在写入成功后调用（主程序用它刷新界面）。"""

    def __init__(self, parent, on_applied=None):
        super().__init__(parent)
        self.on_applied = on_applied

        # ---- 服务开关 ----
        svc = ttk.LabelFrame(self, text="服务开关", padding=12)
        svc.pack(fill="x", padx=12, pady=(12, 4))
        self.explain_on = tk.BooleanVar()
        self.translate_on = tk.BooleanVar()
        ttk.Checkbutton(svc, text="解释服务", variable=self.explain_on).grid(
            row=0, column=0, sticky="w", padx=(0, 24))
        ttk.Checkbutton(svc, text="翻译服务", variable=self.translate_on).grid(
            row=0, column=1, sticky="w")

        # ---- 模型配置 ----
        llm = ttk.LabelFrame(self, text="模型配置", padding=12)
        llm.pack(fill="x", padx=12, pady=4)
        self.llm_var = tk.StringVar()
        self.claude_model_var = tk.StringVar()
        self.local_model_var = tk.StringVar()
        self.local_base_var = tk.StringVar()

        ttk.Label(llm, text="LLM").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(llm, textvariable=self.llm_var,
                     values=[d for d, _ in LLM_DISPLAY],
                     state="readonly", width=24).grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(llm, text="Claude 模型").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(llm, textvariable=self.claude_model_var, width=26).grid(
            row=1, column=1, sticky="w", pady=4)

        ttk.Label(llm, text="本地模型").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(llm, textvariable=self.local_model_var, width=26).grid(
            row=2, column=1, sticky="w", pady=4)

        ttk.Label(llm, text="本地地址").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(llm, textvariable=self.local_base_var, width=26).grid(
            row=3, column=1, sticky="w", pady=4)

        ttk.Label(llm, text="Claude 模型留空 = 跟随 ~/.claude/settings.json",
                  foreground="#999").grid(row=4, column=0, columnspan=2,
                                          sticky="w", pady=(2, 0))
        ttk.Label(llm, text="本地地址默认 http://localhost:11434（Ollama）",
                  foreground="#999").grid(row=5, column=0, columnspan=2,
                                          sticky="w", pady=(2, 0))

        # ---- 翻译设置 ----
        f = ttk.LabelFrame(self, text="翻译设置（引擎固定 Google）", padding=12)
        f.pack(fill="x", padx=12, pady=4)

        self.common_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.popup_var = tk.StringVar()
        self.font_var = tk.StringVar()
        self.min_var = tk.StringVar()
        self.max_var = tk.StringVar()

        # 常用语言 ↔ 目标语言
        lang_row = ttk.Frame(f)
        lang_row.grid(row=0, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Label(lang_row, text="常用语言").pack(side="left")
        ttk.Combobox(lang_row, textvariable=self.common_var,
                     values=[d for d, _ in LANG_DISPLAY],
                     state="readonly", width=18).pack(side="left", padx=(6, 10))
        ttk.Label(lang_row, text="⇄", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Combobox(lang_row, textvariable=self.target_var,
                     values=[d for d, _ in LANG_DISPLAY],
                     state="readonly", width=18).pack(side="left", padx=(10, 6))
        ttk.Label(lang_row, text="目标语言").pack(side="left")

        r = 1
        ttk.Label(f, text="弹窗秒数").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Spinbox(f, textvariable=self.popup_var, from_=1, to=120,
                    width=22).grid(row=r, column=1, sticky="w", pady=4)
        r += 1

        ttk.Label(f, text="译文字号").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Spinbox(f, textvariable=self.font_var, from_=8, to=40,
                    width=22).grid(row=r, column=1, sticky="w", pady=4)
        r += 1

        ttk.Label(f, text="最小字数").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Spinbox(f, textvariable=self.min_var, from_=1, to=100,
                    width=22).grid(row=r, column=1, sticky="w", pady=4)
        r += 1

        ttk.Label(f, text="最大字数").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Spinbox(f, textvariable=self.max_var, from_=50, to=20000,
                    width=22).grid(row=r, column=1, sticky="w", pady=4)

        btns = ttk.Frame(self, padding=(12, 4, 12, 4))
        btns.pack(fill="x")
        ttk.Button(btns, text="应用并生效", command=self.apply).pack(side="left")
        ttk.Button(btns, text="刷新", command=self.reload).pack(side="left", padx=6)

        self.status = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status, foreground="#666",
                  padding=(12, 0, 12, 12)).pack(fill="x")

        self.reload()

    def reload(self):
        cfg = cl.read_config()
        self.explain_on.set(bool(cfg.get("service_explain", True)))
        self.translate_on.set(bool(cfg.get("service_translate", True)))
        self.llm_var.set(LLM_DISPLAY_OF.get(cfg.get("llm", "claude"), cfg.get("llm", "claude")))
        self.claude_model_var.set(cfg["llms"]["claude"].get("model", "") or _settings_model())
        self.local_model_var.set(cfg["llms"]["local"].get("model", ""))
        self.local_base_var.set(cfg["llms"]["local"].get("base_url", "")
                                or "http://localhost:11434")
        self.common_var.set(DISPLAY_OF.get(cfg["common_lang"], cfg["common_lang"]))
        self.target_var.set(DISPLAY_OF.get(cfg["target_lang"], cfg["target_lang"]))
        self.popup_var.set(str(cfg["popup_seconds"]))
        self.font_var.set(str(cfg.get("font_size", 14)))
        self.min_var.set(str(cfg["min_len"]))
        self.max_var.set(str(cfg["max_len"]))
        self.status.set("已读取当前配置")

    def apply(self):
        try:
            popup = float(self.popup_var.get())
            font_size = int(self.font_var.get())
            min_len = int(self.min_var.get())
            max_len = int(self.max_var.get())
        except ValueError:
            messagebox.showerror("错误", "数字字段格式不对（弹窗秒数 / 译文字号 / 最小 / 最大字数）")
            return

        llm = LLM_CODE_OF.get(self.llm_var.get())
        if llm not in cl.LLM_CHOICES:
            messagebox.showerror("错误", f"未知 LLM：{self.llm_var.get()}")
            return

        common = CODE_OF.get(self.common_var.get())
        target = CODE_OF.get(self.target_var.get())
        if common is None or target is None:
            messagebox.showerror("错误", "请选择常用语言与目标语言")
            return
        if common == target:
            messagebox.showerror("错误", "常用语言与目标语言不能相同")
            return

        cfg = cl.read_config()
        cfg["service_explain"] = bool(self.explain_on.get())
        cfg["service_translate"] = bool(self.translate_on.get())
        cfg["llm"] = llm
        cfg["common_lang"] = common
        cfg["target_lang"] = target
        cfg["popup_seconds"] = popup
        cfg["font_size"] = font_size
        cfg["min_len"] = min_len
        cfg["max_len"] = max_len
        cfg["engine"] = "google"
        cm = self.claude_model_var.get().strip()
        lm = self.local_model_var.get().strip()
        lb = self.local_base_var.get().strip() or "http://localhost:11434"
        cfg["llms"]["claude"]["model"] = cm        # 留空 = 跟随 ~/.claude/settings.json
        if lm:
            cfg["llms"]["local"]["model"] = lm
        cfg["llms"]["local"]["base_url"] = lb

        try:
            targets = cl.write_config(cfg)
        except RuntimeError as e:
            messagebox.showerror("错误", str(e))
            return

        msg = f"已写入 {len(targets)} 处，即时生效"
        if self.on_applied:
            try:
                self.on_applied()
            except Exception:
                pass
        self.status.set(msg)


def open_settings(parent, on_applied=None):
    """在主程序里打开设置窗口（Toplevel，同一进程）。"""
    win = tk.Toplevel(parent)
    win.title(APP_TITLE)
    win.resizable(False, False)
    try:
        win.transient(parent)
    except Exception:
        pass

    panel = ConfigPanel(win, on_applied=on_applied)
    panel.pack(fill="both", expand=True)

    win.update_idletasks()
    try:
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        win.geometry(f"+{px + max(0, (pw - w) // 2)}+{py + max(0, (ph - h) // 3)}")
    except Exception:
        pass
    win.lift()
    try:
        win.focus_force()
    except Exception:
        pass
    return win


def main():
    """独立运行时：单独一个设置窗口（仅开发用；正式版只有一个 exe）。"""
    root = tk.Tk()
    root.withdraw()
    open_settings(root)
    root.mainloop()


if __name__ == "__main__":
    main()
