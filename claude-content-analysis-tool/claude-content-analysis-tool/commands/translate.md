---
description: Claude content analysis tool 控制台（on / off / status / llm / explain / translate）
argument-hint: [on|off|status|llm <claude|local>|explain <on|off>|translate <on|off>]
---

你是 **Claude content analysis tool** 的控制台。只根据 `$ARGUMENTS` 执行下面**其中一条**命令（用 Bash 工具跑），然后把输出如实告诉用户，不要做任何多余操作：

- 参数为空 或 `status`：运行 `python "${CLAUDE_PLUGIN_ROOT}/status.py"`
- `on`：运行 `python "${CLAUDE_PLUGIN_ROOT}/start_translate.py"`
- `off`：运行 `python "${CLAUDE_PLUGIN_ROOT}/stop_translate.py"`
- `llm claude` / `llm local`：运行 `python "${CLAUDE_PLUGIN_ROOT}/config.py" llm <第二个参数>`
- `explain on` / `explain off`：运行 `python "${CLAUDE_PLUGIN_ROOT}/config.py" explain <第二个参数>`
- `translate on` / `translate off`：运行 `python "${CLAUDE_PLUGIN_ROOT}/config.py" translate <第二个参数>`

注意：`llm` 只能跟 `claude` / `local`；`explain` / `translate` 只能跟 `on` / `off`。其它值直接拒绝并提示用户可选值。翻译引擎固定为 Google。
