# 第十九轮：真实白屏及零尺寸内容区

用户确认屏幕上的 Inspector 也确实白屏，排除只有截图捕获白屏的解释。

新增 diagnostics.js，在 DOM 就绪、加载、错误、重绘和尺寸改变时经 CEP 宿主回调写入独立 JSON 收据，只记录本扩展的尺寸和样式，不读取用户文档内容。部署前页面备份为 backups/phase19_index_before_diagnostics.html。

首次实测（tests/receipts/cep_page_1793359347135_126151_*.json）：页面 readyState=complete，visibility=visible，背景 rgb(32,35,42)，devicePixelRatio=1.5，但 innerWidth=0、innerHeight=0、bodyWidth=0。一次 CSS 重绘未解决白屏。

按 Adobe CEP 12 CSInterface.js 的 resizeContent 接口，在检测到零尺寸时仅调用一次 resizeContent(540,440)。第二次实测（tests/receipts/cep_page_1793359452178_120698_*.json）：resized 和 after-content-resize 阶段 width=540、height=440、bodyWidth=508、bodyHeight=169，证明内容区尺寸补偿生效。但之后重新抓取窗口仍白屏，所以视觉呈现未修复，不将内容区恢复等同于面板恢复。

官方接口参考：https://raw.githubusercontent.com/Adobe-CEP/CEP-Resources/master/CEP_12.x/CSInterface.js

最终保留零尺寸补偿及独立诊断；未修改 GPU、DPI、账户、安全设置或重启 Au。上一轮 GPU 参数已从安装清单撤回，但本次进程沿用宿主缓存的参数，故尺寸测试不能单独证明默认GPU路径下效果；后续干净宿主启动仍需复验。

测试：node --check 通过；maintenance/test_cep_diagnostics.cjs 验证零尺寸修复、有尺寸不干预、生成 JSX 的字符串转义，以及有限次重绘。未增加 Controller 公开接口。
