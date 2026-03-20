# 操作日志

| 时间 | 操作类型 | 影响文件 | 变更摘要 | 原因 | 测试状态 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-03-16 10:00 | 新增 | docs/operateLog.md | 创建操作日志文件 | 初始化项目文档结构 | 无需测试 |
| 2026-03-16 10:30 | 修改 | main.py, ui/dialogs/create_milestone_dialog.py, ui/widgets/milestone_detail_panel.py, ui/dialogs/tag_dialog.py, ui/widgets/milestone_list_panel.py, core/snapshot.py | 增强日志系统 | 增加全局异常捕获及关键业务操作（里程碑/标签增删）的日志记录 | 待测试 |
| 2026-03-16 10:45 | 修改 | ui/widgets/milestone_list_panel.py | 新增搜索筛选栏 | 在里程碑列表顶部添加 MilestoneToolBar，支持搜索展开及筛选下拉菜单 | 待测试 |
| 2026-03-16 11:00 | 修改 | ui/widgets/milestone_list_panel.py | 优化搜索与筛选 | 1. 搜索仅匹配名称/说明；2. 新增日期选择器筛选；3. 新增标签多选弹窗及 Chip 显示；4. 完善空状态提示 | 待测试 |
| 2026-03-16 11:15 | 修改 | ui/widgets/milestone_list_panel.py | 代码重构 | 移除冗余的 Chip 组件，重构 TagBadge 以支持筛选模式，实现组件复用 | 待测试 |
| 2026-03-16 11:30 | 修改 | ui/widgets/milestone_list_panel.py | UI 优化 | 改造 TagFilterDialog，使用流式布局 + 可选中的 TagBadge 替代复选框列表，支持发光选中效果 | 待测试 |
| 2026-03-20 10:20 | 修改 | ui/main_window.py | 修复新建仓库时不刷新侧边栏 | 增加 connectSignalToSlot 注册欢迎页的信号 | 待测试 |
| 2026-03-20 10:20 | 修改 | ui/dialogs/create_milestone_dialog.py | 增加系统预设标签支持 | 注入一组全局常量标签供快速选择并持久化 | 待测试 |
| 2026-03-20 10:25 | 修复 | ui/dialogs/create_milestone_dialog.py | 修复无父节点时闪退报错 | 追加对获取最初始始发版本时的对象属性判空容错 | 待测试 |
| 2026-03-20 10:30 | 优化 | ui/dialogs/create_milestone_dialog.py | 修复暂存单个文件卡死 | 将 O(N) 的 UI 整树重建变为 O(1) 跨视图物理节点移动 `takeTopLevelItem` | 待测试 |
| 2026-03-20 10:45 | 修复 | ui/dialogs/create_milestone_dialog.py | 修复新建系统标签崩溃 | 处理遗落的 `pt.name` 为字典访问 `pt["name"]` 消除 AttributeError | 待测试 |
| 2026-03-20 10:45 | 修复 | core/snapshot.py | 修复提交里程碑卡死崩溃 | 删除重复传递的两遍 `snapshot_id` 消除 SyntaxError | 待测试 |
| 2026-03-20 10:45 | 修复 | ui/dialogs/create_milestone_dialog.py | 修复点击文件夹暂存依然卡死 | 利用 `QTimer.singleShot` 将大量文件对象的底层回收推移出当前的点击事件栈 | 待测试 |
| 2026-03-20 10:45 | 修复 | app/app_config.py | 修复侧导航栏排序随心所欲 | 改良 `add_repo` 规则，将 `insert(0, path)` 改为 `.append(path)` 维持首尾顺序 | 待测试 |
| 2026-03-20 10:55 | 重构 | ui/dialogs/create_milestone_dialog.py | 彻底根绝目录操作及暂存单文件时的闪退卡死问题 | 废弃物理修改 UI 节点（`takeChild`, `clear` 等），引入极简 O(N) `setHidden` 属性可见性切换算法，实现 0 时延、不操作对象内存的绝对安全变更 | 待测试 |
| 2026-03-20 15:55 | 新增 | .gitignore | 添加 Git 忽略配置 | 忽略 Python 缓存文件及常用忽略项，保持仓库整洁 | 无需测试 |
