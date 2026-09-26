# 迁移到 0.6.0

0.6.0 统一主题继承、选择信号、页面所有权和时间参数命名。这是一个破坏性版本：
下文列出的旧名称不提供别名、弃用包装或兼容参数。

## 迁移速查

| 旧调用或行为 | 0.6.0 调用或行为 |
| --- | --- |
| 子组件 `theme=None` 跟随全局，忽略父组件主题 | 继承最近的主题父组件，没有时才跟随全局 |
| `window.hideTitleBar()` 永久删除标题栏 | `window.setTitleBarVisible(False)` 隐藏，传 `True` 恢复 |
| `page = navigation.removePage(index)` | `page = navigation.takePage(index)` |
| `window.content` | `window.centralWidget()` |
| `window.cornerRadius` | `window.cornerRadius()`；写入使用 `setCornerRadius(value)` |
| `segments.group.checkedId()` | `segments.currentIndex()` |
| `segments.buttons[index].setChecked(True)` | `segments.setCurrentIndex(index)` |
| `segments.group.idClicked` | `segments.itemActivated`；如需监听程序设置，使用 `currentChanged` |
| `segments.buttons[index].setText(text)` | `segments.setItemText(index, text)` |
| `segments.buttons[index].setEnabled(enabled)` | `segments.setItemEnabled(index, enabled)` |
| 读取整个 `segments.buttons` 列表 | `count()` 加 `button(index)`；返回的按钮由组件持有 |
| `DockConfig(anim_duration=250, hide_delay=500)` | `DockConfig(animation_duration_ms=250, hide_delay_ms=500)` |
| `ModernMetrics(animation_duration=250)` | `ModernMetrics(animation_duration_ms=250)` |
| `window.initWindow()`、窗口/对话框/消息框的 `apply_window_style()` | 删除调用；初始化和样式刷新由组件内部负责 |

## 1. 主题统一继承

所有提供 `theme()` / `setTheme()` 的组件按下面的顺序解析主题：

1. 自己通过构造参数或 `setTheme(theme)` 设置的局部覆盖。
2. 最近的、提供主题的父组件，中间可以经过普通 `QWidget`。
3. `theme_manager()` 的全局主题。

`setTheme(None)` 清除局部覆盖。父组件修改主题、控件重新挂接、祖先重新挂接时，
继承主题会更新，包括隐藏控件和只修改自定义颜色 token 的情况。

```python
from PySide6.QtWidgets import QWidget
from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernTabWidget,
    ModernWindow,
)

window = ModernWindow(theme=DARK_THEME)
container = QWidget(window)
tabs = ModernTabWidget(container)  # 现在继承深色，不再直接跟随全局。
tabs.setTheme(LIGHT_THEME)  # 固定此组件及其未覆盖主题的后代为浅色。
tabs.setTheme(None)  # 恢复继承 window 的深色。
```

受默认行为变更影响的组件包括 `ModernWindow`、`ModernDialog`、`ModernMessageBox`、
`ModernTabWidget`、`NavigationView`、`NavigationSidebar` 和 `TabView`。
开关、组合框、分段控件、工具栏本来就继承父组件，现在共享同一套更新机制。

确实需要某个子组件始终跟随全局时，应显式绑定全局管理器：

```python
from pyside6_modern_widgets import theme_manager

manager = theme_manager()
tabs.setTheme(manager.theme())
manager.themeChanged.connect(tabs.setTheme)
```

仅调用一次 `setTheme(manager.theme())` 是固定当前快照，不会自动跟随后续全局变化。
要恢复普通继承，先断开这条连接，再调用 `tabs.setTheme(None)`。

组件新增 `themeChanged(theme)`，有效主题改变并应用后发出；重复设置相同主题不重复发出。
业务页面应连接其主题所属组件的信号，而非一律监听全局管理器。

Flyout 使用锚点作为主题来源；通知卡片继承其 `NotificationManager`。
原生菜单继续使用 Qt palette 继承，`ModernMenuBar` 自动继承最近的主题父组件，
这两类控件不提供 `setTheme()`。

## 2. 侧栏索引信号

`NavigationSidebar` 删除当前项目之前的项目后，现在会发出新的 `currentChanged(index)`。
例如选中索引 2、删除索引 0，将收到 `currentChanged(1)`。回调中读取索引和项目内容时，
状态已经更新。

如果业务代码以前在删除后手动调整缓存索引，应改为以 `currentChanged` 为准，避免重复调整。

## 3. 标题栏显隐可恢复

```python
window.setTitleBarVisible(False)
window.setTitleBarVisible(True)
assert window.isTitleBarVisible()
```

隐藏不删除标题栏、自定义控件或信号连接。标题对齐、图标设置等在恢复后保留。
窗口隐藏或修改 window flags 不会重置这个偏好。macOS 原生交通灯按钮也遵循该设置。
`isTitleBarVisible()` 返回配置偏好，窗口未显示时也可以为 `True`；
`Popup` 等窗口类型和平台能力仍可能限制实际显示。

`setTitleVisible()` 仍只控制标题文字，`setIconVisible()` 仍只控制标题栏图标。
不再支持通过 `hideTitleBar()` 永久删除内部结构。

## 4. 页面移除与所有权转移

| 操作 | 返回值 | 页面父对象 | 页面销毁时机 |
| --- | --- | --- | --- |
| `NavigationView.removePage(index)` | `None` | 保留 | 原容器销毁时销毁，或由调用者提前处理 |
| `TabView.removeTab(index)` / `ModernTabWidget.removeTab(index)` | `None` | 保留 | 同上，保持 Qt 原有语义 |
| `NavigationView.takePage(index)` | 页面或 `None` | 设为 `None` | 交由调用者管理 |
| `TabView.takeTab(index)` / `ModernTabWidget.takeTab(index)` | 页面或 `None` | 设为 `None` | 交由调用者管理 |
| `ModernWindow.takeCentralWidget()` | 页面或 `None` | 设为 `None` | 交由调用者管理 |

移除和取出的页面均隐藏；无效索引不改变状态，`take` 返回 `None`。
`setCentralWidget(new_widget)` 仍删除之前由该窗口持有的中心组件。
如果想复用旧组件，应先取出：

```python
page = navigation.takePage(index)
if page is not None:
    other_navigation.addPage(page, "Moved page")

previous = window.takeCentralWidget()
window.setCentralWidget(new_content)
if previous is not None:
    previous.deleteLater()  # 或挂接到其他容器。
```

`centralWidget()` 取代公开的 `content` 属性。它只读取，不会创建内部布局。
`NavigationView` 也新增 `indexOf(page)` 和 `setCurrentWidget(page)`，无需操作内部堆栈来选择页面。

## 5. 分段控件使用索引接口

```python
from pyside6_modern_widgets import ModernSegmentedControl

segments = ModernSegmentedControl(["All", "Open", "Closed"])
segments.currentChanged.connect(lambda index: print("Current:", index))
segments.itemActivated.connect(lambda index: print("Clicked:", index))
segments.setCurrentIndex(2)
segments.setItemText(1, "In progress")
segments.setItemEnabled(1, False)

button = segments.button(0)
if button is not None:
    button.setToolTip("Show every item")
```

`currentChanged` 包括程序设置和用户切换；重复设置相同索引不发出。
`itemActivated` 只报告按钮激活，重复点击当前项仍发出。
空控件的 `currentIndex()` 是 -1；无效索引的 setter 不做操作。
程序可以设置有效索引，包括被禁用的项目，与 Qt 按钮的程序设置行为一致。

高级用法可通过 `button(index)` 获取借用的 `QPushButton`；
直接调用该按钮的 `setChecked(True)` 也会触发组件的 `currentChanged`。
不要删除、重新挂接这些内部按钮或改变其 exclusive/checkable 结构。
`group` 和 `buttons` 属性已经移除。

## 6. 工具栏继承窗口尺寸配置

`window.addToolBar("Tools")` 现在把窗口的 `ModernMetrics` 传给创建的 `ModernToolBar`，
包括其溢出菜单。若旧代码为补偿配置遗漏而再次修改内部 toolbar metrics，可删除该补偿。
传入已有的 `QToolBar` / `ModernToolBar` 时，保留该工具栏自己的配置。

## 7. 命名、单位和类型

所有上述可配置时间参数都使用毫秒，采用 `_ms` 后缀；数值本身不需要换算：

```python
from pyside6_modern_widgets import DockConfig, ModernMetrics

dock_config = DockConfig(animation_duration_ms=250, hide_delay_ms=800)
metrics = ModernMetrics(animation_duration_ms=0)
```

`ModernWindow`、`ModernDialog`、`ModernMessageBox` 通过 `cornerRadius()` 读取圆角，
通过 `setCornerRadius(radius)` 修改。窗口初始化和样式应用方法已设为内部实现；
子类应在 `super().__init__()` 后构建自己的布局，通过 `setTheme()`、`setCornerRadius()`
和其他公开 setter 更新外观。

`addToolBar(title)` 的类型现在明确为 `ModernToolBar`。`addTab` / `insertTab`、窗口尺寸
setter 提供精确重载，便于类型检查发现错误参数。
导航图标接受 `QIcon | QStyle.StandardPixmap | None`；
`addTitleBarButton()` 的图标接受 `QIcon | str`，回调接受无参数或一个 `bool` 参数。
标题栏自定义控件的 `align` 仅接受 `"left"` / `"right"`，其他值会抛出 `ValueError`。

## 同版本的通知与 Dock 调整

0.6.0 还包含先前未发布的通知 Handle 和 Dock 状态 API 调整。
使用旧通知 ID、`duration`、`max_queued`、`setEnabled()` 等调用的应用，
请同时按 [README 的通知迁移表](../README.md#notifications) 改为 Handle API。
Dock 的设置通过 `config()` / `setConfig()` 获取和原子更新；
显式 `collapse()` 不受 `auto_hide` 限制，条件命令返回是否成功。
如使用过未发布的 `DockRestoreTrigger`、`restore_trigger`、`handle_draggable`、
`setRestoreTrigger()` 或 `setHandleDraggable()`，改用 `DockHandleMode`、`handle_mode`
和 `setHandleMode()`，不再组合互相冲突的行为开关。
