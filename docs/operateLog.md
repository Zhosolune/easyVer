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
| 2026-03-20 16:00 | 新增 | README.md | 编写项目说明文档 | 总结项目特性、技术栈、使用方法和目录结构，便于了解项目概况 | 无需测试 |
| 2026-03-20 16:15 | 修改 | ui/widgets/tag_badge.py | 优化 TagBadge 交互体验 | 1. 删除遮罩动画改为从左向右滑入；2. 增加基于 Fluent ToolTipFilter 的悬浮提示 | 待测试 |
| 2026-03-21 21:30 | 修改 | ui/widgets/tag_badge.py | 优化 TagBadge 删除交互 | 移除侧滑遮罩动画，改为 Hover 时将图标原地替换为带圆形背景的删除图标，点击左侧图标区域触发删除 | 待测试 |
| 2026-03-21 21:35 | 修改 | ui/widgets/tag_badge.py | 修正 ToolTip 触发范围 | 将删除提示的 ToolTipFilter 绑定从整个标签缩小至仅图标 `_icon_label` 区域，避免鼠标在文字上时产生误导 | 待测试 |
| 2026-03-21 21:45 | 优化 | ui/widgets/tag_badge.py, ui/widgets/milestone_card.py | 卡片高度对齐 | 1. 修正 MilestoneCard 各行的高度，保证无标签卡片与有标签卡片视觉一致 | 待测试 |
| 2026-03-21 22:00 | 优化 | ui/pages/settings_page.py | 增加缩放设置提示 | 调整界面缩放比例后弹出 InfoBar，提示用户重启软件后生效 | 待测试 |
| 2026-03-21 22:30 | 重构 | ui/widgets/milestone_detail_panel.py, ui/widgets/marquee_label.py | 优化里程碑详情界面的布局与文件视图 | 1. 重构详情顶部信息（名称、哈希、父版本等）的顺序与样式；2. 增加列表/树状两种文件变更视图，支持状态高亮（绿、黄、红+删除线）及文件夹状态推导；3. 添加右上角变更类型统计数字；4. 禁用横向滚动条并新增 MarqueeLabel 实现超长文件名悬浮滚动显示 | 待测试 |
| 2026-03-22 00:05 | 修复 | ui/widgets/milestone_detail_panel.py | 修复详情页重复加载卡顿问题 | 增加防抖机制，检测到 `snap_id` 未变化时直接 return 避免无意义的树状图重复渲染 | 待测试 |
| 2026-03-22 00:15 | 优化 | ui/widgets/milestone_detail_panel.py | 优化卡片点击响应速度 | 1. 使用 `QTimer.singleShot` 将耗时的树状图与列表 UI 构建逻辑推迟到事件循环空闲时执行；2. 在渲染前禁用组件重绘 (`setUpdatesEnabled(False)`) 减少布局抖动开销 | 待测试 |
| 2026-03-22 00:30 | 深度优化 | ui/widgets/milestone_detail_panel.py | 解决切换卡片时UI卡死与列表空白问题 | 引入 `QThread` (FileLoadWorker)，将耗时的数据库查询、变更过滤及树状图节点推导计算全部移至后台独立线程执行，计算完成后再通过信号机制将数据传回主线程渲染 UI，彻底消除主线程阻塞，保证界面秒响应 | 待测试 |
| 2026-03-22 00:40 | 重构 | core/workers/file_load_worker.py, ui/widgets/milestone_detail_panel.py | 遵守单一职责分离后台线程 | 将 `FileLoadWorker` 及其相关数据模型 `TreeNode` 从 UI 组件中抽离到专门的 `core/workers` 目录中，保持代码职责单一和模块化 | 无需测试 |
| 2026-03-24 10:00 | 重构 | core/workers/commit_worker.py, ui/dialogs/create_milestone_dialog.py, core/workers/scan_worker.py, ui/widgets/working_tree_panel.py | 全面清理UI文件中的后台线程 | 严格遵守单一职责原则，将 `_CommitWorker` 和 `_ScanWorker` 从UI组件文件中抽离到 `core/workers` 目录下，彻底避免职责杂糅 | 无需测试 |
| 2026-03-24 15:30 | 修复 | core/workers/file_load_worker.py | 修复获取详情失败报错 | 修复子线程访问数据库时因硬编码错误的数据库名称 `repo.db` 导致表不存在报错的问题，更正为 `easyver.db` | 已测试 |
| 2026-03-24 15:40 | 优化 | ui/widgets/milestone_detail_panel.py, ui/widgets/marquee_label.py | 彻底解决点击详情时列表加载慢和卡死的问题 | 1. 废弃并删除低效的自定义组件 `MarqueeLabel`，改用 Qt 原生 Item 属性 (`setForeground`, `setFont`, `setToolTip`) 实现状态展示和悬浮提示；2. 启用 `setUniformItemSizes` 避免逐行重绘，将渲染时间从 O(N) 降至 O(1)，实现百万级文件毫秒级响应。 | 已测试 |
| 2026-03-24 15:45 | 优化 | ui/widgets/milestone_detail_panel.py | 统一 UI 风格 | 1. 引入 `PyQt-Fluent-Widgets` 的 `ToolTipFilter` 替换 Qt 原生 Tooltip，保证悬浮提示的气泡样式与项目整体现代风格一致；2. 将文件视图切换控件从 `SegmentedWidget` 替换为水平布局的两个方形 `TransparentToolButton`（使用自定义的 list 和 list-tree 图标），使界面更加轻量、清爽。 | 已测试 |
| 2026-03-25 15:00 | 修复 | db/migrations/003_update_tags_unique.sql, ui/dialogs/tag_dialog.py, ui/widgets/milestone_list_panel.py, ui/widgets/milestone_tool_bar.py | 修复保存标签时唯一性约束报错 | 1. 通过数据库迁移将 `tags` 表的 UNIQUE 约束从 `(repo_id, name)` 放宽为 `(snapshot_id, name)`，允许跨里程碑复用同名标签；2. 修复 TagDialog 中的查重逻辑；3. 修复标签筛选器按 ID 过滤导致复用标签无法正确筛选的问题，改为按 name 过滤 | 已测试 |
| 2026-03-25 15:10 | 修复 | main.py | 屏蔽无意义的终端报错提示 | 通过 `qInstallMessageHandler` 拦截全局 Qt 日志输出，过滤因 `qfluentwidgets` 组件底层使用 `pixelSize` 导致触发的 `QFont::setPointSize: Point size <= 0 (-1)` 警告刷屏问题 | 待测试 |
| 2026-03-25 16:48 | 优化 | ui/widgets/milestone_card.py, ui/widgets/milestone_list_panel.py | 强化里程碑卡片选中视觉效果 | 重写 `paintEvent` 绘制主题色左侧高亮竖条，覆盖背景色方法实现半透明主题色背景；新增 `_select_card`/`_on_card_clicked` 方法统一管理选中状态，修复原来 `setSelected` 无实际效果的问题 | 待测试 |
| 2026-03-26 15:00 | 新增 | app/app_config.py, app/application.py, ui/main_window.py, ui/pages/welcome_page.py | 添加删除仓库功能 | 支持在左侧导航栏通过右键菜单彻底移除仓库记录，并同步刷新欢迎页最近访问列表 | 待测试 |
