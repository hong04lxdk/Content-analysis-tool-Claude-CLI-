Claude content analysis tool

绑定 **Claude Code** 启动的 Windows 桌面小工具（插件名 `claude-content-analysis-tool`）。启动即显示主窗口，提供两个可独立开关的服务：

- **解释**：输入内容 → LLM（Claude setting / 本地 Ollama）分析解释。
- **翻译**：复制任意文字 → 光标旁弹窗；**常用语言 ⇄ 目标语言双向互译**，其它语言不翻。引擎为 Google，无需 API Key。


### 绿色版（不需要插件）

```bash
python build_release.py          # 或双击 build_release.bat
```

产物 `dist/ContentAnalysisTool-0.1.0/`（exe + 便携 `config.json` + 说明）及同名 zip，双击 exe 即可运行。

## 使用

1. **解释**：输入内容 → 「解释」或 `Ctrl+Enter`。
2. **翻译**：输入内容 → 「翻译」；或在任意程序里复制文字，光标旁弹出译文。
3. **设置**：右上角「设置」或托盘右键「设置」→ 开关服务、配置模型与翻译参数 → 「应用并生效」。
   修改 Claude 模型后需手动点「刷新」（没有定时自动刷新）。

Claude Code 内使用插件技能 `translate`：

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

仓库里的 `config.json` 是默认模板，不含个人模型、端点或 Token。

## 打包

```bash
pip install -r claude-content-analysis-tool/requirements.txt
python build_release.py          # --no-zip 只出目录；--keep-dist 保留旧目录
```

## 目录

```text
claude-content-analysis-tool/
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
