# Computer Use 路径转换诊断

2026-10-30：已从实际 Node 启动进程捕捉到 Codex `sandbox -c default_permissions="node_repl" -c permissions.node_repl=...` 命令。生成的 filesystem 表含 D 盘根目录。

使用同一已安装 Codex 0.166.0-alpha.5.1、相同项目目录，对命令 `cmd.exe /c ver` 做隔离对照：

| 测试 | 结果 |
| --- | --- |
| 配置 filesystem 中仅额外加入 `D:\`（只读） | exit 1，`permission path cannot be represented losslessly` |
| 根目录写成重复反斜杠 | 同样失败 |
| Windows `\\?\C:\...\bin` 扩展路径 | exit 0 |
| 原聊天权限转为 Node 使用的配置格式，排除 `D:\` | exit 0 |
| 原权限通过 sandbox-state-json 传递且排除 `D:\` | exit 0 |

结论：当前已安装运行时对配置表中的盘符根目录存在路径往返转换问题。原来的磁盘 ACL 错误是另一处失败，改 ACL 不能修复这个转换错误。MXC 已按用户授权禁用，elevated 仍会触发同一转换错误。

修复准备：`maintenance/repair_chat_workspace_roots.ps1` 等待 ChatGPT 桌面进程全部退出后，备份 `.codex-global-state.json`，仅设置本聊天 `thread-writable-roots` 为项目目录和该聊天可视化目录。不会修改会话历史或磁盘 ACL。应用重开后还需检查实际权限上下文并完成 Computer Use 窗口及截图测试；当前不能标记修复完成。

执行状态将写入 `_runtime/workspace_root_repair.json`，若失败保留原因。备份保存在原用户配置目录内。
