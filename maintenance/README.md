# Audition Controller 维护入口（第七轮）

- rebuild_phase07_catalog.py：读取冻结的 360 项第六轮基线，按真实收据重建 375 项开发台账、90 个公开方法、P0 证据映射及剩余功能清单。
- verify_workspace.py：独立检查 API、前轮收据、Native Audition 工程/导出、数十个哈希检查及全部 292 项单元测试。推荐使用 --sdk --full-tests。

    cd D:\computer\Adobe\Audition
    python -B maintenance\rebuild_phase07_catalog.py
    python -B maintenance\verify_workspace.py --sdk --full-tests

注意：只用正式维护入口。Phase07 一次性 GUI、Native、调试脚本已归档在 archives，不要直接对用户工程重跑。
