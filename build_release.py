#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 ContentAnalysisTool 打包成可直接分发的「现成版本」。

产物（dist 目录）：
  ContentAnalysisTool-<版本>/
      ContentAnalysisTool.exe   主窗口 + 设置，单文件、无控制台、免安装
      config.json               便携配置（默认值，不含任何个人设置）
      README.md                 说明
      使用说明.txt
  ContentAnalysisTool-<版本>-win64.zip   上面整个目录的压缩包

用法：
    python build_release.py             # 打包并压缩
    python build_release.py --no-zip    # 只生成目录
    python build_release.py --keep-dist # 不清理旧目录（默认会先删同一版本目录）
"""
import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "claude-content-analysis-tool")
DIST = os.path.join(ROOT, "dist")

PYFILES = ["translate_tool.py", "config_lib.py", "config_gui.py", "config.py",
           "status.py", "set_engine.py", "start_translate.py", "stop_translate.py"]

REQUIRED = PYFILES + ["config.json", "README.md", "requirements.txt",
                      ".claude-plugin/plugin.json", "commands/translate.md"]

USAGE_TEXT = """Claude content analysis tool  {ver}

【启动】
双击 ContentAnalysisTool.exe 即可（绿色版，不需要安装 Python）。

【主窗口】
- 输入内容 → 「解释」：由 LLM（Claude setting / 本地模型）分析解释。
- 输入内容 → 「翻译」：常用语言 ⇄ 目标语言 双向互译。
- 选中任意文字并按 Ctrl+C 复制，光标旁会弹出翻译（只翻常用语言和目标语言，
  其它语言不翻译）。
- 右上角「设置」：服务开关、模型配置、翻译设置。改完点「应用并生效」。

【LLM】
- Claude setting：读取 ~/.claude/settings.json 的
  ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / model。
- 本地模型：Ollama，地址默认 http://localhost:11434，模型名填 Ollama 里已有的。

【配置文件】
- config.json 与本 exe 同目录 = 便携配置（推荐，随目录一起带走）。
- 若 exe 所在目录不可写，会自动改用
  %LOCALAPPDATA%\\ContentAnalysisTool\\config.json。

【卸载】
绿色程序，删除整个目录即可。
"""


def log(msg):
    print(msg)


def read_version():
    p = os.path.join(SRC, ".claude-plugin", "plugin.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f).get("version") or "0.0.0"


def check_project():
    missing = [rel for rel in REQUIRED if not os.path.exists(os.path.join(SRC, rel))]
    if missing:
        log("*** 项目文件缺失，无法打包：")
        for m in missing:
            log("    " + m)
        return False
    log("  项目文件齐全（%d 项）" % len(REQUIRED))
    return True


def compile_all():
    import py_compile
    ok = True
    for f in PYFILES:
        try:
            py_compile.compile(os.path.join(SRC, f), doraise=True)
        except Exception as e:
            log("  COMPILE FAILED: %s\n  %s" % (f, e))
            ok = False
    log("  编译通过" if ok else "  编译失败")
    return ok


def build_exe(outdir):
    """PyInstaller 打成单个无控制台 exe。"""
    work = tempfile.mkdtemp(prefix="cat-build-")
    try:
        rc = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
             "--onefile", "--windowed",
             "--name", "ContentAnalysisTool",
             "--distpath", outdir,
             "--workpath", os.path.join(work, "build"),
             "--specpath", work,
             "translate_tool.py"],
            cwd=SRC).returncode
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if rc != 0:
        log("  PyInstaller 失败（返回码 %d）" % rc)
        return False
    exe = os.path.join(outdir, "ContentAnalysisTool.exe")
    if not os.path.exists(exe):
        log("  未生成 exe")
        return False
    log("  exe：%s（%.1f MB）" % (exe, os.path.getsize(exe) / 1024 / 1024))
    return True


def write_config_template(path):
    sys.path.insert(0, SRC)
    try:
        import config_lib
        cfg = json.loads(json.dumps(config_lib.DEFAULTS))  # 深拷贝，不含个人设置
        # 发布版不写死 Claude 模型：留空 = 跟随使用者的 ~/.claude/settings.json
        cfg["llms"]["claude"]["model"] = ""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    finally:
        sys.path.pop(0)
    log("  便携配置：config.json（默认值）")


def write_usage(path, ver):
    # utf-8-sig：让 Windows 记事本正确识别中文
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(USAGE_TEXT.format(ver=ver))
    log("  使用说明：使用说明.txt")


def make_zip(folder, zip_path):
    if os.path.exists(zip_path):
        os.remove(zip_path)
    base = os.path.dirname(folder)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _, files in os.walk(folder):
            for name in files:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, base)
                z.write(full, rel)
    log("  压缩包：%s（%.1f MB）" % (zip_path, os.path.getsize(zip_path) / 1024 / 1024))


def main(argv):
    no_zip = "--no-zip" in argv
    keep_dist = "--keep-dist" in argv

    if not os.path.isdir(SRC):
        log("找不到源码目录：" + SRC)
        return 1

    ver = read_version()
    name = "ContentAnalysisTool-%s" % ver
    outdir = os.path.join(DIST, name)
    zip_path = os.path.join(DIST, name + "-win64.zip")

    log("[1/5] 检查项目 ...")
    if not check_project():
        return 1

    log("[2/5] 编译检查 ...")
    if not compile_all():
        log("*** 编译失败，未打包 ***")
        return 1

    log("[3/5] 生成 %s ..." % os.path.basename(outdir))
    if os.path.isdir(outdir) and not keep_dist:
        shutil.rmtree(outdir)
    os.makedirs(outdir, exist_ok=True)

    log("[4/5] 打包主程序 ...")
    if not build_exe(outdir):
        log("*** 打包失败 ***")
        return 1

    shutil.copy2(os.path.join(SRC, "README.md"), os.path.join(outdir, "README.md"))
    write_config_template(os.path.join(outdir, "config.json"))
    write_usage(os.path.join(outdir, "使用说明.txt"), ver)

    log("[5/5] 压缩 ...")
    if no_zip:
        log("  已跳过（--no-zip）")
    else:
        make_zip(outdir, zip_path)

    log("")
    log("===== 打包完成 =====")
    log("版本目录：%s" % outdir)
    if not no_zip:
        log("分发包  ：%s" % zip_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
