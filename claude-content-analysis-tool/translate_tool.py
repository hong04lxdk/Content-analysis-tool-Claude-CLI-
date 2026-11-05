#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude content analysis tool
绑定 Claude Code 启动，启动即显示主窗口：

- 解释服务：在输入框输入内容 → LLM（Claude setting / 本地模型）分析解释。
- 翻译服务：选中文字（复制进剪贴板）→ 谷歌翻译，常用语言 ↔ 目标语言双向互译；
  其它语言不翻译。主窗口里也可直接翻译输入框里的内容。

只依赖 requests + 标准库（tkinter / ctypes）。
"""

import os
import json
import queue
import time
import ctypes
import ctypes.wintypes as wt
import threading
import tkinter as tk
from tkinter import ttk

import requests

import config_lib as cl

_http = requests.Session()  # 复用连接

APP_TITLE = "Claude content analysis tool"

BASE = os.path.dirname(os.path.abspath(__file__))  # 源码目录；打包成 exe 后是临时解包目录


def _runtime_dir():
    """运行状态目录（PID / show.flag）：取实际生效的 config.json 所在目录（cache 副本）。"""
    try:
        targets = cl.find_targets()
        if targets:
            return os.path.dirname(targets[0])
    except Exception:
        pass
    return BASE


RUNTIME_DIR = _runtime_dir()
CONFIG_PATH = os.path.join(RUNTIME_DIR, "config.json")
PID_PATH = os.path.join(RUNTIME_DIR, "run", "translate.pid")

LANG_NAMES = cl.LANG_NAMES


def load_config():
    return cl.read_config()


# ----------------------------------------------------------------------------
# Win32 基础（剪贴板 / 光标 / 屏幕）
# ----------------------------------------------------------------------------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CF_UNICODETEXT = 13

user32.GetClipboardSequenceNumber.restype = ctypes.c_uint32
user32.OpenClipboard.restype = ctypes.c_bool
user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = [ctypes.c_uint]
user32.CloseClipboard.restype = ctypes.c_bool
user32.GetCursorPos.restype = ctypes.c_bool
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetForegroundWindow.restype = wt.HWND
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_bool
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.OpenProcess.restype = ctypes.c_void_p
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.CloseHandle.restype = ctypes.c_bool
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class POINT(ctypes.Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG)]


def clipboard_sequence():
    return user32.GetClipboardSequenceNumber()


def read_clipboard_text():
    """读取剪贴板里的文本（仅 CF_UNICODETEXT）。拿不到返回 None。"""
    for _ in range(5):
        if user32.OpenClipboard(None):
            try:
                h = user32.GetClipboardData(CF_UNICODETEXT)
                if h:
                    p = kernel32.GlobalLock(h)
                    if p:
                        try:
                            return ctypes.wstring_at(p)
                        finally:
                            kernel32.GlobalUnlock(h)
            finally:
                user32.CloseClipboard()
            return None
        time.sleep(0.02)
    return None


def cursor_pos():
    p = POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def screen_size():
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def foreground_is_self():
    """前台窗口是否属于本进程（避免在自家窗口里复制文字又触发翻译）。"""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        pid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == os.getpid()
    except Exception:
        return False


def enable_dpi_awareness():
    """按物理像素渲染，避免高分屏（>100% 缩放）下 Tk 文字发虚。"""
    try:
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness.restype = ctypes.c_long
        for aw in (2, 1):  # PER_MONITOR_DPI_AWARE -> SYSTEM_DPI_AWARE
            if shcore.SetProcessDpiAwareness(aw) == 0:  # S_OK
                return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ----------------------------------------------------------------------------
# 翻译（谷歌，常用语言 ↔ 目标语言 双向）
# ----------------------------------------------------------------------------
def _base_lang(code):
    return str(code or "").lower().replace("_", "-").split("-")[0]


def _google_request(text, tl):
    """调谷歌翻译，返回 (译文, 识别出的源语言代码)。"""
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "auto", "tl": tl, "dt": "t", "q": text}
    r = _http.get(url, params=params, timeout=15,
                  headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    r.raise_for_status()
    data = r.json()
    parts = [seg[0] for seg in data[0] if seg and seg[0]]
    result = "".join(parts).strip()
    detected = ""
    try:
        if len(data) > 2 and data[2]:
            detected = data[2]
    except Exception:
        pass
    return result, detected


def translate_bidirectional(text, cfg):
    """常用语言 ↔ 目标语言双向互译。

    返回 (译文, 目标语言代码)；若内容不属于两种语言之一，返回 (None, None)。
    """
    common = cfg["common_lang"]
    target = cfg["target_lang"]
    if _base_lang(common) == _base_lang(target):
        return None, None

    # 先翻到「常用语言」，顺带拿到谷歌识别出的源语言
    first, detected = _google_request(text, common)
    d = _base_lang(detected)
    if d == _base_lang(target):
        return first, common            # 目标语言 → 常用语言（这次结果就是译文）
    if d == _base_lang(common):
        second, _ = _google_request(text, target)
        return second, target           # 常用语言 → 目标语言（再翻一次）
    return None, None                   # 其它语言：不翻译


# ----------------------------------------------------------------------------
# LLM（解释服务）：Claude setting / 本地模型
# ----------------------------------------------------------------------------
def _claude_settings():
    """从 ~/.claude/settings.json 读 Claude 的认证与模型配置（不落盘、不外传）。"""
    p = os.path.expanduser("~/.claude/settings.json")
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8-sig") as f:
            d = json.load(f)
    except Exception:
        return {}
    env = d.get("env", {}) or {}
    return {
        "base": env.get("ANTHROPIC_BASE_URL", ""),
        "token": env.get("ANTHROPIC_AUTH_TOKEN", "") or env.get("ANTHROPIC_API_KEY", ""),
        "model": d.get("model", ""),
    }


def _llm_claude(system, user, cfg):
    e = cfg["llms"].get("claude", {})
    senv = _claude_settings()
    base = (e.get("base_url") or senv.get("base") or "https://api.anthropic.com").rstrip("/")
    token = (e.get("auth_token") or senv.get("token")
             or os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"))
    model = e.get("model") or senv.get("model") or "claude-sonnet-5"
    if not token:
        raise RuntimeError("未找到 Claude 认证（~/.claude/settings.json 里没有 ANTHROPIC_AUTH_TOKEN）")

    url = base + "/v1/messages"
    headers = {
        "content-type": "application/json",
        "x-api-key": token,
        "authorization": "Bearer " + token,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": model,
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    r = _http.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    out = "".join(parts).strip()
    if not out:
        raise RuntimeError("Claude 返回为空")
    return out


def _llm_local(system, user, cfg):
    e = cfg["llms"].get("local", {})
    model = e.get("model") or "qwen2.5:7b"
    base = (e.get("base_url") or "http://localhost:11434").rstrip("/")
    r = _http.post(base + "/api/chat", json={
        "model": model, "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }, timeout=120)
    r.raise_for_status()
    out = (r.json().get("message", {}).get("content", "")).strip()
    if not out:
        raise RuntimeError("本地模型返回为空")
    return out


def llm_complete(system, user, cfg):
    if cfg.get("llm", "claude") == "local":
        return _llm_local(system, user, cfg)
    return _llm_claude(system, user, cfg)


def explain(text, cfg):
    lang = LANG_NAMES.get(cfg.get("common_lang", "zh-CN"), cfg.get("common_lang", "zh-CN"))
    system = (f"你是内容分析助手。用{lang}简洁清晰地分析并解释用户提供的内容："
              "先用一两句话给出结论或含义，再分点说明关键要点，必要时指出潜在问题或建议。"
              "不要重复原文，直接给分析。")
    return llm_complete(system, text, cfg)


# ----------------------------------------------------------------------------
# 主程序
# ----------------------------------------------------------------------------
class ContentAnalysisApp:
    def __init__(self):
        self.cfg = load_config()
        self._last_text = ""
        self._seq = clipboard_sequence()
        self._popup = None
        self._busy = False
        self._results = queue.Queue()          # 划词翻译结果 (text, result, target_name, cfg)
        self._work = queue.Queue(maxsize=1)    # 只保留最新一条待翻译
        self._ui_results = queue.Queue()       # 主窗口解释/翻译结果 (text, is_error)

        try:
            os.makedirs(os.path.dirname(PID_PATH), exist_ok=True)
            with open(PID_PATH, "w") as f:
                f.write(str(os.getpid()))
        except Exception:
            pass

        threading.Thread(target=self._worker_loop, daemon=True).start()

        enable_dpi_awareness()
        self.root = tk.Tk()
        self._build_main_window()
        self._poll()

    # ---------------- 主窗口 ----------------
    def _build_main_window(self):
        root = self.root
        root.title(APP_TITLE)
        root.geometry("600x560")
        root.minsize(460, 420)
        root.configure(bg="#ffffff")

        top = ttk.Frame(root, padding=(12, 10, 12, 2))
        top.pack(fill="x")

        # 标题行：输入内容（左）+ 设置（右，同一水平），下面的输入框保持原设计、整行铺满
        header = ttk.Frame(top)
        header.pack(fill="x")
        ttk.Label(header, text="输入内容",
                  font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        ttk.Button(header, text="设置", command=self._open_settings).pack(side="right")

        self.input_text = tk.Text(top, height=7, wrap="word", undo=True,
                                  font=("Microsoft YaHei UI", 11),
                                  relief="solid", borderwidth=1)
        self.input_text.pack(fill="both", expand=False, pady=(4, 0))
        self.input_text.bind("<Control-Return>", lambda e: (self._do_explain(), "break")[1])

        btns = ttk.Frame(root, padding=(12, 6, 12, 2))
        btns.pack(fill="x")
        self.explain_btn = ttk.Button(btns, text="解释", command=self._do_explain)
        self.explain_btn.pack(side="left")
        self.translate_btn = ttk.Button(btns, text="翻译", command=self._do_translate)
        self.translate_btn.pack(side="left", padx=6)
        ttk.Button(btns, text="清空", command=self._clear).pack(side="left")
        ttk.Button(btns, text="刷新", command=self._do_refresh).pack(side="left", padx=6)
        self.status_var = tk.StringVar(value="")
        ttk.Label(btns, textvariable=self.status_var, foreground="#888").pack(side="right")

        out = ttk.Frame(root, padding=(12, 4, 12, 6))
        out.pack(fill="both", expand=True)
        ttk.Label(out, text="结果", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        wrap = ttk.Frame(out)
        wrap.pack(fill="both", expand=True, pady=(4, 0))
        self.output_text = tk.Text(wrap, wrap="word", state="disabled",
                                   font=("Microsoft YaHei UI", 11),
                                   relief="solid", borderwidth=1)
        sb = ttk.Scrollbar(wrap, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.output_text.pack(side="left", fill="both", expand=True)

        footer = ttk.Frame(root, padding=(12, 0, 12, 8))
        footer.pack(fill="x")
        self.info_var = tk.StringVar(value="")
        ttk.Label(footer, textvariable=self.info_var, foreground="#667").pack(side="left")

        root.protocol("WM_DELETE_WINDOW", self._quit)
        self._refresh_services()

    def _refresh_services(self):
        self.cfg = load_config()
        ex = bool(self.cfg.get("service_explain", True))
        tr = bool(self.cfg.get("service_translate", True))
        if not self._busy:
            self.explain_btn.configure(state=("normal" if ex else "disabled"))
            self.translate_btn.configure(state=("normal" if tr else "disabled"))
        llm = self.cfg.get("llm", "claude")
        if llm == "local":
            model = self.cfg["llms"]["local"].get("model", "") or "默认"
            base = self.cfg["llms"]["local"].get("base_url", "") or "http://localhost:11434"
            model = f"{model} @ {base}"
        else:
            model = (self.cfg["llms"]["claude"].get("model", "")
                     or _claude_settings().get("model", "") or "默认")
        llm_label = cl.LLM_LABELS.get(llm, llm)
        c = LANG_NAMES.get(self.cfg["common_lang"], self.cfg["common_lang"])
        t = LANG_NAMES.get(self.cfg["target_lang"], self.cfg["target_lang"])
        self.info_var.set(
            f"LLM: {llm_label} · {model}    ·    {c} ⇄ {t}    ·    "
            f"解释{'开' if ex else '关'} / 翻译{'开' if tr else '关'}"
        )

    def _do_refresh(self):
        self._refresh_services()
        self._set_status("已刷新配置")

    def _open_settings(self):
        """在同一进程里打开设置窗口（唯一的 exe，不再有独立配置程序）。"""
        win = getattr(self, "_settings_win", None)
        try:
            if win is not None and win.winfo_exists():
                win.lift()
                win.focus_force()
                return
        except Exception:
            pass
        import config_gui
        self._settings_win = config_gui.open_settings(self.root,
                                                      on_applied=self._on_settings_applied)

    def _on_settings_applied(self):
        self._refresh_services()
        self._set_status("设置已应用")

    def _set_status(self, s):
        self.status_var.set(s)

    def _set_output(self, text):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
        self.output_text.configure(state="disabled")

    def _set_busy(self, busy):
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.explain_btn.configure(state=state)
        self.translate_btn.configure(state=state)
        if not busy:
            self._refresh_services()

    def _show_window(self):
        """把主窗口恢复显示并置顶到前台（顺带刷新一次配置）。"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.root.attributes("-topmost", True)
            self.root.after(400, lambda: self.root.attributes("-topmost", False))
            self._refresh_services()
        except Exception:
            pass

    def _input(self):
        return self.input_text.get("1.0", "end").strip()

    def _clear(self):
        self.input_text.delete("1.0", "end")
        self._set_output("")
        self._set_status("")

    # ---------------- 主窗口：解释 / 翻译 ----------------
    def _do_explain(self):
        if self._busy:
            return
        text = self._input()
        if not text:
            self._set_status("请先输入内容")
            return
        cfg = load_config()
        if not cfg.get("service_explain", True):
            self._set_status("解释服务已关闭（在配置里开启）")
            return
        self._set_busy(True)
        self._set_output("⏳ 分析中…")
        self._set_status("分析中…")

        def work():
            try:
                self._ui_results.put(("explain", explain(text, cfg), False))
            except Exception as e:
                self._ui_results.put(("explain", f"⚠️ 解释失败：{e}", True))

        threading.Thread(target=work, daemon=True).start()

    def _do_translate(self):
        if self._busy:
            return
        text = self._input()
        if not text:
            self._set_status("请先输入内容")
            return
        cfg = load_config()
        if not cfg.get("service_translate", True):
            self._set_status("翻译服务已关闭（在配置里开启）")
            return
        self._set_busy(True)
        self._set_output("⏳ 翻译中…")
        self._set_status("翻译中…")

        def work():
            try:
                res, tgt = translate_bidirectional(text, cfg)
                if res is None:
                    self._ui_results.put(
                        ("translate", "（该内容不属于常用语言 / 目标语言，未翻译）", False))
                else:
                    self._ui_results.put(("translate", res, False))
            except Exception as e:
                self._ui_results.put(("translate", f"⚠️ 翻译失败：{e}", True))

        threading.Thread(target=work, daemon=True).start()

    # ---------------- 划词翻译 ----------------
    def _poll(self):
        # 0) 「显示主窗口」信号（单实例二次启动时写入 cache\run\show.flag）
        try:
            flag = os.path.join(os.path.dirname(PID_PATH), "show.flag")
            if os.path.exists(flag):
                os.remove(flag)
                self._show_window()
        except Exception:
            pass

        # 1) 主窗口的解释 / 翻译结果
        try:
            while True:
                kind, text, is_err = self._ui_results.get_nowait()
                self._set_output(text)
                self._set_status("出错" if is_err else "完成")
                self._set_busy(False)
        except queue.Empty:
            pass

        # 2) 划词翻译结果
        try:
            while True:
                src, result, target_name, cfg = self._results.get_nowait()
                if result is None:
                    self._close_popup()  # 其它语言：静默关掉占位
                else:
                    self._show(src, result, cfg, target_name=target_name, pending=False,
                               dismiss_after=cfg.get("popup_seconds", 8))
        except queue.Empty:
            pass

        # 3) 轮询剪贴板变化
        try:
            seq = clipboard_sequence()
            if seq != self._seq:
                self._seq = seq
                text = read_clipboard_text()
                if text:
                    text = text.strip()
                    if text and text != self._last_text:
                        self._last_text = text
                        if not foreground_is_self():
                            self._on_text(text)
        except Exception:
            pass

        # 4) 不再自动刷新配置：只在用户点主窗口「刷新」或设置里「应用并生效」时刷新
        self.root.after(250, self._poll)

    def _on_text(self, text):
        cfg = load_config()
        if not cfg.get("service_translate", True):
            return
        if len(text) < cfg["min_len"]:
            return
        if len(text) > cfg["max_len"]:
            text = text[: cfg["max_len"]] + " …"

        # 立即弹出「翻译中…」占位，消除等待感
        self._show(text, "⏳ 翻译中…", cfg, pending=True, dismiss_after=30)

        item = (text, cfg)
        try:
            self._work.put_nowait(item)
        except queue.Full:
            try:
                self._work.get_nowait()
                self._work.put_nowait(item)
            except queue.Full:
                pass

    def _worker_loop(self):
        while True:
            text, cfg = self._work.get()
            try:
                result, target_name = translate_bidirectional(text, cfg)
            except Exception as e:
                result, target_name = f"⚠️ 翻译失败：{e}", None
            self._results.put((text, result, target_name, cfg))

    # ---------------- 弹窗 ----------------
    def _bind_dismiss(self, widget):
        widget.bind("<Button-1>", lambda e: self._close_popup())
        for child in widget.winfo_children():
            self._bind_dismiss(child)

    def _show(self, source, result, cfg, target_name=None, pending=False, dismiss_after=None):
        self._close_popup()
        x, y = cursor_pos()
        sw, sh = screen_size()

        top = tk.Toplevel(self.root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg="#cbd5e1")  # 1px 边框色

        body = tk.Frame(top, bg="#ffffff", padx=14, pady=12)
        body.pack(padx=1, pady=1)

        common = LANG_NAMES.get(cfg["common_lang"], cfg["common_lang"])
        target = LANG_NAMES.get(cfg["target_lang"], cfg["target_lang"])
        tk.Label(body, text=f"文A  {common} ⇄ {target}",
                 bg="#ffffff", fg="#94a3b8",
                 font=("Microsoft YaHei UI", 9), anchor="w").pack(fill="x")

        if source:
            src = " ".join(source.split())
            if len(src) > 160:
                src = src[:160] + " …"
            tk.Label(body, text=src, bg="#ffffff", fg="#94a3b8",
                     font=("Segoe UI", 9), wraplength=380,
                     justify="left", anchor="w").pack(fill="x", pady=(6, 8))

        if len(result) > 800:
            result = result[:800] + " …"
        res_fg = "#94a3b8" if pending else "#0f172a"
        try:
            font_size = int(cfg.get("font_size", 14))
        except (TypeError, ValueError):
            font_size = 14
        font_size = max(8, min(font_size, 40))
        tk.Label(body, text=result, bg="#ffffff", fg=res_fg,
                 font=("Microsoft YaHei UI", font_size), wraplength=380,
                 justify="left", anchor="w").pack(fill="x")

        top.update_idletasks()
        w = top.winfo_reqwidth()
        h = top.winfo_reqheight()
        px, py = x + 14, y + 18
        if px + w > sw - 4:
            px = x - w - 14
        if py + h > sh - 4:
            py = y - h - 18
        top.geometry(f"+{max(0, px)}+{max(0, py)}")

        self._bind_dismiss(top)
        if dismiss_after:
            top.after(int(dismiss_after * 1000), lambda p=top: self._close_if(p))
        self._popup = top

    def _close_if(self, popup):
        """只关闭「还是当前弹窗」的那个，避免旧占位的定时器误关新结果。"""
        if self._popup is popup:
            self._close_popup()

    def _close_popup(self):
        if self._popup is not None:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None

    # ---------------- 退出 ----------------
    def _quit(self):
        try:
            os.remove(PID_PATH)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


def running_pid():
    """PID 文件里记录的进程还活着就返回 pid，否则 None。"""
    try:
        pid = int(open(PID_PATH).read().strip())
    except Exception:
        return None
    if pid <= 0:
        return None
    try:
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h:
            kernel32.CloseHandle(h)
            return pid
    except Exception:
        pass
    return None


def main():
    # 单实例：主程序已经在跑时不再开第二个，只请求它把窗口显示出来
    pid = running_pid()
    if pid:
        try:
            os.makedirs(os.path.dirname(PID_PATH), exist_ok=True)
            with open(os.path.join(os.path.dirname(PID_PATH), "show.flag"), "w") as f:
                f.write("1")
        except Exception:
            pass
        return
    ContentAnalysisApp().run()


if __name__ == "__main__":
    main()
