# Claude content analysis tool

绑定 **Claude Code** 启动的 Windows 桌面小工具（插件名 `claude-content-analysis-tool`）。启动即显示主窗口，提供两个可独立开关的服务：

- **解释**：输入内容 → LLM（Claude setting / 本地 Ollama）分析解释。
- **翻译**：复制任意文字 → 光标旁弹窗；**常用语言 ⇄ 目标语言双向互译**，其它语言不翻。引擎为 Google，无需 API Key。

> Windows 10/11 · Python 3.8+ · 依赖仅 `requests`

## 功能

- 启动即主窗口，关闭窗口即退出；不随 Windows 自启
- 剪贴板划词翻译，弹窗自动关闭、字号可调
- 解释服务支持 Claude setting（复用 `~/.claude/settings.json`）与本地 Ollama
- 单实例：重复启动只唤醒已有窗口
- 图形设置面板（主窗口右上角「设置」）
- 可打包成单文件绿色版 `ContentAnalysisTool.exe`

## 安装

### 作为 Claude Code 插件

需要 Python 3.8+，且 `python` 在 PATH 中可用。

```bash
claude plugin marketplace add <你的GitHub用户名>/claude-content-analysis-tool-marketplace
claude plugin install claude-content-analysis-tool@claude-content-analysis-tool-marketplace --scope user
```

重启 Claude Code 会话，`SessionStart` hook 会自动拉起工具。安装后运行的是 cache 副本：
`~/.claude/plugins/cache/claude-content-analysis-tool-marketplace/claude-content-analysis-tool/0.1.0/`。

### 绿色版（不需要插件）

```bash
python build_release.py          # 或双击 build_release.bat
```

产物 `dist/ContentAnalysisTool-0.1.0/`（exe + 便携 `config.json` + 说明）及同名 zip，双击 exe 即可运行。

## 使用

1. **解释**：输入内容 → 「解释」或 `Ctrl+Enter`。
2. **翻译**：输入内容 → 「翻译」；或在任意程序里复制文字，光标旁弹出译文。
3. **设置**：右上角「设置」→ 开关服务、配置模型与翻译参数 → 「应用并生效」。
   修改 Claude 模型后需手动点「刷新」（没有定时自动刷新）。

Claude Code 内使用插件技能 `translate`：

```text
/claude-content-analysis-tool:translate status|on|off|llm <claude|local>|explain <on|off>|translate <on|off>
```

也可以直接运行源码命令：`python start_translate.py` / `stop_translate.py` / `status.py` / `config.py show`。

## 配置

配置查找顺序：插件 cache → 源码/便携目录 → `%LOCALAPPDATA%\ContentAnalysisTool\config.json`。

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

| 字段 | 说明 |
|------|------|
| `llm` | `claude`（Claude setting）或 `local`（本地模型） |
| `common_lang` / `target_lang` | 双向互译的两个语言 |
| `service_explain` / `service_translate` | 服务开关 |
| `popup_seconds` / `font_size` | 弹窗秒数 / 译文字号（8~40） |
| `min_len` / `max_len` | 过短不翻 / 过长截断 |
| `llms.claude` | 留空则复用 `~/.claude/settings.json` 的端点、Token 与模型 |
| `llms.local` | Ollama 模型名与地址 |

仓库里的 `config.json` 是默认模板，不含个人模型、端点或 Token。

## 打包

```bash
pip install -r claude-content-analysis-tool/requirements.txt
python build_release.py          # --no-zip 只出目录；--keep-dist 保留旧目录
```

## 目录

```text
claude-content-analysis-tool-marketplace/
├─ .claude-plugin/marketplace.json
├─ claude-content-analysis-tool/     # 插件本体
│  ├─ .claude-plugin/plugin.json     # 含 SessionStart hook
│  ├─ translate_tool.py              # 主程序：主窗口 + 划词翻译
│  ├─ config_gui.py / config_lib.py  # 设置面板 / 配置读写
│  ├─ start_translate.py / stop_translate.py / status.py
│  ├─ commands/translate.md          # Claude Code 技能 translate
│  └─ config.json
├─ build_release.py / build_release.bat
└─ dist/                             # 打包产物（已忽略）
```

## 常见问题

- **复制后没弹窗**：只在复制（写剪贴板）时触发；前台是工具自身、文本过短/过长或翻译服务关闭时不会弹。
- **本地模型失败**：确认 Ollama 已启动，地址与 `ollama list` 中的模型名正确。
- **Claude setting 失败**：`~/.claude/settings.json` 需有 `ANTHROPIC_BASE_URL` 和 `ANTHROPIC_AUTH_TOKEN`（或 `ANTHROPIC_API_KEY`）。

## 许可证

暂未指定许可证，如需公开使用请自行添加 `LICENSE`。
