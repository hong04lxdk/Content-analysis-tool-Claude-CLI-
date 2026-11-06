# Claude content analysis tool

绑定 **Claude Code** 启动的 Windows 桌面小工具（插件 `claude-content-analysis-tool`）。启动即显示主窗口，提供两个可独立开关的服务：

- **解释**：输入内容 → LLM（Claude setting / 本地 Ollama）分析解释。
- **翻译**：复制文字 → 光标旁弹窗；常用语言 ⇄ 目标语言双向互译，其它语言不翻。引擎 Google，无需 Key。

`Ctrl+Enter` 触发解释；关闭主窗口收进系统托盘（左键托盘唤回，右键菜单「设置 / 退出」）。程序另有 `ContentAnalysisTool.exe` 绿色版。需要 Python 3.8+（含 tkinter），依赖仅 `requests`。

## 安装

```bash
# <仓库目录> 换成本仓库实际路径
claude plugin validate "<仓库目录>/claude-content-analysis-tool"
claude plugin marketplace add "<仓库目录>"
claude plugin install claude-content-analysis-tool@claude-content-analysis-tool-marketplace --scope user
```

`SessionStart` hook 用 PATH 中的 `python` 拉起工具，重启 Claude Code 会话后自动显示主窗口。安装后运行的是 cache 副本：

```
~/.claude/plugins/cache/claude-content-analysis-tool-marketplace/claude-content-analysis-tool/0.1.0/
```

改源码后需同步到该目录并重启工具。

## 用法

1. 输入内容 →「解释」（或 `Ctrl+Enter`），结果显示在输出区。
2. 输入内容 →「翻译」；或在任意程序里复制文字，光标旁弹窗。
3. 右上角「设置」或托盘右键「设置」：服务开关、模型配置、翻译参数；改完点「应用并生效」。
   修改 Claude 模型后需手动点「刷新」。
4. 关闭主窗口 = 收进托盘继续后台工作；左键托盘图标显示主窗口，右键「退出」才真正结束进程。

Claude Code 内通过插件技能 `translate` 控制：

```text
/claude-content-analysis-tool:translate status|on|off
/claude-content-analysis-tool:translate llm claude|local
/claude-content-analysis-tool:translate explain on|off
/claude-content-analysis-tool:translate translate on|off
```

不依赖 Claude 时可直接运行：

```bash
python start_translate.py   # 启动（已运行则唤醒；优先启动 ContentAnalysisTool.exe）
python stop_translate.py    # 停止
python status.py            # 状态
```

主程序是单文件 `ContentAnalysisTool.exe`（`translate_tool.py` 打包）：主窗口与设置（同进程 `Toplevel`）都在里面，单实例运行。

## 配置

配置文件查找顺序：插件 cache → 源码/便携目录 → `%LOCALAPPDATA%\ContentAnalysisTool\config.json`。

```json
{
  "llm": "claude",
  "common_lang": "zh-CN",
  "target_lang": "en",
  "service_explain": true,
  "service_translate": true,
  "popup_seconds": 8,
  "font_size": 14,
  "min_len": 2,
  "max_len": 2000,
  "llms": {
    "claude": { "model": "", "base_url": "", "auth_token": "" },
    "local": { "model": "qwen2.5:7b", "base_url": "http://localhost:11434" }
  }
}
```

`llms.claude` 留空 = 复用 `~/.claude/settings.json` 的 `ANTHROPIC_BASE_URL`、`ANTHROPIC_AUTH_TOKEN`（或 `ANTHROPIC_API_KEY`）与 `model`；填了就覆盖。

命令行修改（即时生效）：

```bash
python config.py show
python config.py llm local
python config.py commonlang zh-CN
python config.py lang en
python config.py popup 12
python config.py fontsize 16
python config.py minlen 3
python config.py model <模型名>
python config.py localmodel qwen2.5:7b
python config.py explain off
python config.py translate on
```

## 发布打包

在仓库根目录执行 `python build_release.py`（或双击 `build_release.bat`）：

```
dist/
  ContentAnalysisTool-<版本>/
    ContentAnalysisTool.exe     单文件、无控制台、免安装
    config.json                 便携配置（默认值，不含个人信息）
    README.md
    使用说明.txt
  ContentAnalysisTool-<版本>-win64.zip
```

独立运行时优先读取 exe 同目录的 `config.json`，其次 `%LOCALAPPDATA%\ContentAnalysisTool\config.json`。

## 文件

| 文件 | 说明 |
|------|------|
| `translate_tool.py` | 主程序：主窗口 + 系统托盘 + 剪贴板划词翻译 + 单实例 |
| `config_gui.py` / `config_lib.py` | 设置面板 / 配置读写 |
| `start_translate.py` / `stop_translate.py` / `status.py` | 启动 / 停止 / 状态 |
| `config.py` / `set_engine.py` | 配置命令行 |
| `commands/translate.md` | Claude Code 技能 `translate` |
| `.claude-plugin/plugin.json` | 插件清单（含 SessionStart hook） |
| `config.json` | 默认配置模板 |
