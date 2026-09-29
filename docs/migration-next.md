# 从 0.6.0 迁移到下一版本

本文记录尚未发布的 API 调整；已发布的 0.6.0 迁移说明保持不变。

## 侧栏项目所有权

`NavigationSidebar.removeItem(index)` 现在与页面容器的 `removePage()` /
`removeTab()` 一致：隐藏并移除项目，保留按钮原有的 Qt 父对象，返回 `None`。
按钮仍由原容器持有，随容器销毁；调用者也可以提前调用 `deleteLater()`。

旧代码需要取回按钮时，必须改用 `takeItem(index)`：

```python
# 之前：button = sidebar.removeItem(index)
button = sidebar.takeItem(index)
if button is not None:
    # 按钮已隐藏且 parent() 为 None，由调用者管理。
    button.deleteLater()  # 或挂接到其他容器。
```

两种操作遇到无效索引均不改变状态并返回 `None`。移除后的按钮不再影响侧栏的
选中状态，也不会触发侧栏的 `itemActivated`。

## 侧栏选择信号

`sidebar.button(index)` 返回借用的按钮。对有效按钮调用 `setChecked(True)`，
现在会同步 `currentIndex()` 并在选择改变时发出一次 `currentChanged(index)`；
在 `NavigationView` 中也会同步当前页面。重复设置相同选择不发出信号。

`itemActivated(index)` 仍只报告按钮激活，包括重复点击当前项。
不要删除、重新挂接借用按钮，或修改其 checkable/exclusive 结构；
需要接管按钮时先调用 `takeItem()`。

## TabView 与 Qt 行为对齐

- `insertTab(index, ...)` 的负索引现在表示追加到末尾，与 `QTabWidget` 一致。
  旧代码若使用 `-1` 插入开头，请改用 `0`。
- `setCurrentIndex()` / `setCurrentWidget()` 现在允许程序选择禁用页，
  但不会将页面启用。若应用要求程序选择也跳过禁用页，应先检查 `isTabEnabled()`。
- 用户导航及 `nextTab()` / `previousTab()` 仍跳过禁用页。
