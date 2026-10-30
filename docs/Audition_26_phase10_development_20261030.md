# 第十轮开发记录（未发布验收）

新增14个公开方法，当前110个。保留第九轮台账和原96个接口名称；新增代码不自动计入已验收功能。

## 实现与边界

- edit_production_session：按稳定track_id/clip_id，在工程副本中复制、移动、删除、同轨波纹删除、分割、裁剪、淡化、重叠片段交叉淡化和重命名轨道。拒绝锁定片段；分割、裁剪拒绝循环和时长映射不一致片段。输出新SESX，未完成Au重开验收。
- package_production_session：将工程与所有已解析素材复制到新目录，写入相对路径和SHA256清单；实际搬迁后的Au重开仍未验收。
- session_overlap_report：检测同轨所有片段重叠。
- relink_production_session：明确素材file ID和新路径，可附SHA256；没有自动模糊搜索。
- production_component_inventory / patch_production_component：读取已有组件，修改已有powered和归一化参数。没有实现Rack新建、重排、插件加载或Send新建。
- enqueue_production_job / production_queue_status / run_next_production_job / retry_production_job / mark_production_job_interrupted：SQLite持久队列、事务领取、失败隔离和显式恢复。重试前检查输出冲突；需要先确认旧工作进程已经退出，再标记中断。目前重跑整个任务，没有步骤级断点续跑。
- render_gain_pan_envelope：离线样本级增益和声像插值。单声道用等功率声像输出立体声；立体声使用衰减平衡。不是Au原生包络。
- repair_review_bundle：波形编辑配合before/after WAV、诊断JSON和瞬态候选CSV，需要听审。不是原生Spectral修复。依赖原有波形发布能力。
- mixdown_production_session：按完整路径定位已打开且保存的工程；通过新增文档识别混音结果、轮询完成、解码验证并独占发布。只有干运行测试，未获真实宿主验收。

## 原入口改动

根目录从源码位置推导。multitrack_track_edit新增session_path和save=False：多个多轨工程且没有明确路径时拒绝操作；需要原自动保存行为的调用方必须传save=True。

JSX调用使用跨进程串行锁。锁不阻止人工操作，也不保证超时后的宿主脚本已停止。生产任务的前置产物引用必须带@，修复预检与执行规则不一致。

## 使用

所有新增写入接口默认只规划；执行传confirm=True或CLI的--confirm。输出目录需存在，目标不能已存在。

```powershell
python -B audition_controller.py edit-production-session source.sesx output.sesx edits.json
python -B audition_controller.py relink-session source.sesx output.sesx replacements.json
python -B audition_controller.py overlaps source.sesx
python -B audition_controller.py automation-audio source.wav output.wav points.json
python -B audition_controller.py repair-review source.wav new_review_folder edits.json
python -B audition_controller.py production-mixdown source.sesx mix.wav
python -B maintenance/verify_phase10_development.py
```

编辑JSON示例，ID必须从目标工程读取：

```json
[{"action":"copy","track_id":"10001","clip_id":"0","target_track_id":"10002","start_samples":48000}]
```

包络JSON示例，采样位置必须小于文件总帧数：

```json
[{"sample":0,"gain_db":-6,"pan":-1},{"sample":48000,"gain_db":-6,"pan":1}]
```

## 验证和未完成工作

新增18项针对性测试通过；原第八轮12项调用与批处理边界测试通过。全量结果见tests/receipts/phase10_development_*.json。第九轮发布器固定要求96方法、326测试，不适用于当前开发版发布。

两次真实宿主只读探测超时（8秒和15秒），没有取得版本与文档状态回读。没有关闭或强杀宿主。

未完成：新素材批量导入和轨道创建、原生交叉淡化曲线与听感验收、原生音量关键帧、Pan渲染校准、Rack顺序与预设、Send、步骤级恢复、素材候选搜索、搬迁工程包重开验收、原生Spectral GUI修复、CEP宿主修复、AMIO编译部署、ASIO/录音/控制设备、AAF/OMF/Premiere/5.1。需要真实宿主恢复及相应SDK、素材、硬件条件继续实现验收。

本轮属于开发进展，不能表述为上次建议的全部方向已经完成。

桌面环境第一次全量复验341/341通过（后续又增加3项测试）。执行环境限制导致的13项报错不代表音频逻辑回归；以最新phase10_development收据为准。

最终桌面环境全量复验：344/344通过，110个公开方法，原96个接口名称全部保留。收据：tests/receipts/phase10_development_20261030T012941067151.json。开发版完整签名目录：api/Audition_26_phase10_development_api.json。此结果不包含真实Au混音、SDK、硬件验收。
