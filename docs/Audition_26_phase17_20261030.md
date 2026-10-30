# 第十七轮：CEP 部署及 Premiere 启动核验

已核对安装目录：index.html、panel.js、manifest.xml 均存在，CEP 主进程命令行指向正确页面，渲染、GPU、网络及存储进程均实际存在。Inspector 仍显示白屏；这不能归因于缺失页面文件，也不能把进程存在当作 evalScript 成功。

已备份已安装 panel.js 到 backups/phase17_installed_panel_before_fix.js，部署上一轮的零文档 activeDocument 修复。安装后 SHA256 为 8D442CF2AFDD2512D612D6C63B2E7DAC1B6B97DCCB7C661BA4F323609E9A4C88。此部署未证明白屏已恢复，未重启或强杀 Au。

Premiere 通过现有安装路径单次启动，创建进程 62472；后续未出现可操作 Premiere 窗口，桌面出现“打开一个项目时 Premiere 意外退出”提示。未点击重新打开，未循环启动。最近15分钟 Application 1000/1001 记录没有检索到匹配错误，故未知故障模块，不猜测 GPU 或插件原因。

未完成：CEP 页面渲染与回调、频谱画笔/套索、Premiere 往返、硬件设备及发布签名。上轮软件回归384/384的范围保持不变。本轮无新增公开方法，不宣称全部开发完成。

参考：Adobe CEP 12 Cookbook https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_12.x/Documentation/CEP%2012%20HTML%20Extension%20Cookbook.md
