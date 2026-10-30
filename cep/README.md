# Audition CEP Inspector — 安装完成，宿主加载仍失败

源代码位置：D:\computer\Adobe\Audition\cep\com.openai.audition.inspector
用户级安装：C:\Users\LENOVO\AppData\Roaming\Adobe\CEP\extensions\com.openai.audition.inspector

第六轮确认官方 CEP 12 Cookbook 将 Audition CEP 12 对应的版本列为 AUDT 25.0：
https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_12.x/Documentation/CEP%2012%20HTML%20Extension%20Cookbook.md

因此第六轮自定义清单改为：
- ExtensionManifest Version=7.0
- Host AUDT Version=[25.0,99.9]
- RequiredRuntime CSXS Version=12.0

安装文件与源码 SHA-256 相同。Audition 在零打开文档情况下正常退出、正常启动，新进程响应正常。
但 Window > Extensions 未显示 Inspector，CEP12-AUDT.log 仍为 PlugPlugSetup / PlugPlugAddEventListener internalError。
这显示阻塞尚在 CEP 宿主初始化层面，不能声称面板已成功运行。

前一版 Manifest 备份在 backups/phase06_before_cep12_manifest.xml。
证据：tests/receipts/phase06_cep12_manifest_corrected.json 和 phase06_cep12_relaunch_diagnostic.json。

待下一轮在有 Adobe 可用的 CEP 宿主诊断/官方 SDK 资料后进一步查明；不要为了调试反复强制结束 Audition。
