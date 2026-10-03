# pyside6-modern-widgets

[English](README.md) | 简体中文

适用于 Windows 和 macOS 的 PySide6 桌面控件库。它提供现代窗口标题栏、导航、标签页和常用输入控件，同时尽量保留 Qt 原有的构造方式、信号和交互行为。

- `ModernWindow`、`ModernDialog`、`ModernMessageBox`：带主题外观的窗口、对话框和消息框。
- `ModernMenu`、`ModernMenuBar`、`ModernToolBar`、`ModernToolButton`、`ModernPushButton`：菜单和按钮；Windows 11 上的菜单可使用系统 acrylic 效果。
- `ModernComboBox`、`ModernFontComboBox`、`ModernLineEdit`、`ModernSpinBox`、`ModernDoubleSpinBox`、`ModernDateEdit`、`ModernTimeEdit`、`ModernDateTimeEdit`：选择和单行输入控件。
- `ModernPlainTextEdit`、`ModernTextEdit`、`ModernKeySequenceEdit`：多行文本和快捷键输入。
- `ModernCheckBox`、`ModernRadioButton`、`ModernSwitch`、`ModernSlider`、`ModernScrollBar`、`ModernSegmentedControl`：选择和数值控件。
- `ModernTabWidget`：保留 `QTabWidget` API 的固定标签页；`TabView`：支持添加、关闭和拖动的文档标签页。
- `ModernFlyout`：依附于锚点控件的弹出面板。
- `ModernNotification`、`NotificationManager`：桌面或窗口内通知，支持操作、进度和队列。
- `NavigationSidebar`、`NavigationView`：可折叠侧栏及同步的页面容器。
- `EdgeDockController`：顶层窗口的屏幕边缘吸附和自动隐藏。

导航项可通过 `group` 归组。标题不会占用页面索引；侧栏折叠或分组为空时会隐藏：

```python
navigation.addPage(home_page, "Home")
navigation.addPage(editor_page, "Editor", group="Workspace")
navigation.addPage(files_page, "Files", group="Workspace")
navigation.addPage(settings_page, "Settings", position=NavigationPosition.BOTTOM, group="System")
```

## 支持环境

仅支持 Windows 和 macOS，要求 Python 3.10-3.12、PySide6 6.8.3 和 Fusion 样式。主题背景由 Qt 绘制，并可从桌面壁纸提取颜色。

Windows 上的自定义标题栏保留原生窗口激活、移动、缩放、最小化、最大化、Aero Snap、阴影和系统菜单。Windows 11 还支持 DWM 圆角及最大化按钮的 Snap Layouts；Windows 10 使用方角不透明表面。

macOS 上的 `ModernWindow` 保留原生 `NSWindow` 边框和红黄绿窗口按钮，将主题内容延伸到透明标题栏；不显示 Windows 风格按钮和窗口图标。标题栏双击遵循系统偏好。`ModernMessageBox` 使用原生标题栏拖动，并保留 Qt 的 macOS 内容边距。

## 安装与 0.6.0

当前仓库的 0.6.0 功能**尚未发布**。要使用这份源码，请在仓库根目录运行：

```shell
pip install -e .
```

以下命令安装 PyPI 上最新的已发布版本：

```shell
pip install pyside6-modern-widgets
```

即将发布的 0.6.0 统一了主题继承、选择信号、页面与侧栏项目所有权、标题栏显隐和类型标注。部分 API 不兼容旧版本；升级前请阅读 [0.6.0 迁移指南](docs/migration-0.6.md)。

## PyInstaller

安装后的包会自动注册 PyInstaller hook，通常无需额外指定 hidden import 或数据文件：

```shell
pyinstaller your_app.py
```

## 国际化

库自身的窗口按钮、导航和标签提示、通知辅助文本以及可移植系统菜单，提供英文原文和简体中文翻译。应用传入的页面名称、通知内容和操作文本由应用自行翻译。在创建 `QApplication` 后安装库的翻译器：

```python
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication
from pyside6_modern_widgets import load_translator

app = QApplication([])
widgets_translator = load_translator(QLocale.system(), app)
if widgets_translator is not None:
    app.installTranslator(widgets_translator)
```

运行时安装或卸载翻译器会通过 Qt 的 `LanguageChange` 事件更新现有控件。Qt 标准按钮文字来自单独的 `qtbase` 翻译目录，需要应用自行安装对应翻译器。修改库内文字后，可用 `pyside6-lupdate` 与 `pyside6-lrelease` 更新 `src/pyside6_modern_widgets/translations/` 下的 `.ts` 和 `.qm` 文件；完整命令见[英文说明](README.md#internationalization)。

## 屏幕边缘停靠

将 `EdgeDockController` 绑定到浮动的顶层 `QWidget` 或 `ModernWindow`。指定专用的拖动条时，子控件仍可正常接收鼠标和键盘输入：

```python
from pyside6_modern_widgets import DockSide, EdgeDockController

dock = EdgeDockController(window, drag_widget=drag_strip, auto_hide=True)
dock.dock(DockSide.RIGHT)
dock.setAutoHide(False)  # 停止自动隐藏；仍可手动折叠。
dock.collapse()
dock.expand()  # 从启动器或快捷键重新显示时也使用它。
dock.dismiss()  # 同时隐藏窗口和恢复手柄，不关闭窗口。
dock.setDragWidget(new_drag_strip)
```

默认恢复手柄是一条细条。`DockConfig` 可设置 `handle_icon`、`handle_icon_size`、`handle_padding`、`handle_tooltip`、颜色、边框和形状。图标手柄支持 `DockHandleShape.ROUNDED_RECT` 与 `CIRCLE`；空图标退回细条。尺寸使用 Qt 逻辑像素，运行时可通过 `setHandleIcon()`、`setHandleShape()`、`setHandleIconSize()` 等方法修改，折叠状态下也有效。

`DockHandleMode` 提供 `HOVER_OR_CLICK`、`CLICK` 和 `DRAG_OR_CLICK`。拖动手柄需要显式启用：

```python
from pyside6_modern_widgets import DockHandleMode

dock.setHandleMode(DockHandleMode.DRAG_OR_CLICK)
```

点击会恢复窗口；拖动超过 Qt 的系统阈值后，手柄可跨边缘和显示器移动。放到允许的屏幕边缘附近会保持折叠并重新停靠，放到屏幕内部会展开并取消停靠。按 Escape、失去鼠标捕获或改变屏幕配置会取消正在进行的拖动。该功能需要全局定位和鼠标捕获。

`DockConfig` 控制吸附距离、边距、手柄尺寸与颜色、动画时长、隐藏延迟和允许的边缘。默认 `dock_distance` 为 24 逻辑像素，默认启用左、右、上三边；需要底边时加入 `DockSide.BOTTOM`。`config()` 返回快照，`setConfig()` 原子更新配置。`setAutoHide(False)` 只关闭自动隐藏，不会自动展开已折叠窗口。

`placement()` 返回当前屏幕、边缘及沿边缘的比例位置；应用可自行持久化，并用 `setPlacement()` 恢复。`state()`、`dockSide()`、`isCollapsed()`、`isAttached()` 及相应信号可用于观察状态。`detach()` 永久解除绑定；同一目标同时只能附加一个控制器。窗口已折叠时，`window.hide()` 不会隐藏手柄，请使用 `dock.dismiss()`。Windows 上恢复时会请求原生前台激活。

独立示例运行 `python examples/edge_dock_example.py`；导航示例中也有 **Edge docking** 页面。示例可用 `--language en` 或 `--language zh_CN` 指定启动语言。更多边缘拖动、多显示器和生命周期细节见[英文说明](README.md#screen-edge-docking)。

## 组合框与输入控件

`ModernComboBox` 保留 `QComboBox` 的模型、编辑、验证、补全、选择信号和键盘/鼠标操作。弹出列表沿用 Qt 容器，使用现代菜单的行距、选中背景和外框；Windows 11 上可使用 acrylic，Windows 10 和 macOS 使用不透明表面。调用者设置的视图、委托或显式 palette 仍由调用者控制。

```python
from pyside6_modern_widgets import ModernComboBox

combo = ModernComboBox(parent)
combo.addItem("Windows 11", userData="win11")
combo.addItem("macOS", userData="macos")
combo.setPlaceholderText("Choose a platform")
combo.setCurrentIndex(-1)
combo.currentIndexChanged.connect(lambda index: print(index, combo.currentData()))
combo.setEditable(True)
```

可编辑组合框及其弹出层使用方角，非可编辑组合框保持圆角。默认弹出列表的行高随字体变化；`setView()`、`setItemDelegate()`、`setFrame()` 和 `setPalette()` 保留 Qt 语义。`ModernFontComboBox` 在同一外观上提供原生字体模型、过滤和 `currentFontChanged` 信号。两者都支持 `setTheme()` 局部主题覆盖。

`ModernLineEdit` 保留 `QLineEdit` 的构造方式与文字 API。控件只绘制边框表面，文本编辑、选区、撤销、验证器、输入法、清除按钮和信号仍由 Qt 处理：

```python
from pyside6_modern_widgets import ModernLineEdit

editor = ModernLineEdit("Workspace name")
editor.setClearButtonEnabled(True)
editor.textChanged.connect(print)
```

整数、浮点、日期和时间编辑器分别是 `ModernSpinBox`、`ModernDoubleSpinBox`、`ModernDateEdit`、`ModernTimeEdit` 和 `ModernDateTimeEdit`。它们保留 Qt 的范围、步进、验证、日期分段、日历弹出和信号行为，使用 Fusion 高度与相邻的上下箭头：

```python
from pyside6_modern_widgets import ModernDateTimeEdit, ModernDoubleSpinBox, ModernSpinBox

number = ModernSpinBox()
number.setRange(0, 100)
decimal = ModernDoubleSpinBox()
decimal.setDecimals(3)
date_time = ModernDateTimeEdit()
date_time.setDisplayFormat("yyyy/M/d HH:mm")
```

`ModernPlainTextEdit` 和 `ModernTextEdit` 保留 Qt 的文档、光标、选区、滚动、撤销和输入法行为。`ModernKeySequenceEdit` 保留快捷键录制 API。它们随父组件继承主题，也可传入 `theme`、`metrics` 或调用 `setTheme()`：

```python
from pyside6_modern_widgets import ModernKeySequenceEdit, ModernPlainTextEdit, ModernTextEdit

notes = ModernPlainTextEdit("Notes")
description = ModernTextEdit("<b>Formatted text</b>")
shortcut = ModernKeySequenceEdit()
```

## 选择与数值控件

`ModernCheckBox`、`ModernRadioButton` 继承 Qt 对应控件，保留 Fusion 尺寸、原生鼠标/键盘/快捷键/信号行为。复选框支持三态，单选按钮保留父对象或按钮组的互斥关系。指示器随主题和系统强调色变化，支持禁用、焦点和 RTL 布局。

```python
from pyside6_modern_widgets import ModernCheckBox, ModernRadioButton

check = ModernCheckBox("Enable notifications")
check.setChecked(True)
radio = ModernRadioButton("General")
radio.setChecked(True)
```

`ModernSwitch` 使用 `QCheckBox` 常见的文字/父对象构造方式，以及 `setChecked()`、`toggled(bool)` 和 `clicked(bool)`。可以点击轨道或文字，也可用 Tab、Space 操作。轨道固定为 32×16 逻辑像素，随主题和系统 Accent 色更新；无文字开关应设置 `setAccessibleName()`。

```python
from pyside6_modern_widgets import ModernSwitch

switch = ModernSwitch("Enable notifications")
switch.toggled.connect(lambda enabled: print(enabled))
```

`ModernSlider` 继承 `QSlider` 的范围、步进、键盘、滚轮、跟踪与数值信号。点击轨道直接移到对应数值，拖动圆形滑块持续更新。支持横向、纵向和局部主题覆盖：

```python
from PySide6.QtCore import Qt
from pyside6_modern_widgets import ModernSlider

slider = ModernSlider(Qt.Orientation.Horizontal)
slider.setRange(0, 100)
slider.setValue(35)
slider.valueChanged.connect(print)
```

`ModernScrollBar` 继承 `QScrollBar` 的原生范围、鼠标、滚轮、键盘和信号行为。它使用 Fusion 几何，悬停时手柄在固定轨道内变粗，周围布局不会移动；箭头只在悬停时出现：

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea
from pyside6_modern_widgets import ModernScrollBar

area = QScrollArea()
area.setVerticalScrollBar(ModernScrollBar(Qt.Orientation.Vertical))
area.setHorizontalScrollBar(ModernScrollBar(Qt.Orientation.Horizontal))
```

`ModernSegmentedControl` 按标签顺序创建互斥选项。`currentChanged(index)` 报告程序和用户的选择变化；`itemActivated(index)` 报告按钮激活，包括再次点击当前项。空控件的 `currentIndex()` 为 -1：

```python
from pyside6_modern_widgets import ModernSegmentedControl

segments = ModernSegmentedControl(["All", "Open", "Closed"])
segments.currentChanged.connect(print)
segments.setCurrentIndex(2)
segments.setItemEnabled(1, False)
```

`count()`、`itemText()` / `setItemText()` 和 `isItemEnabled()` / `setItemEnabled()` 访问项目状态。`button(index)` 返回内部按钮的借用引用，无效索引返回 `None`；不要删除或重新挂接借用按钮。导航示例中的 **Combo box**、**Line edit**、**Spin editors**、**More inputs**、**Choice controls** 和 **Scroll bars** 页面提供原生与现代控件对照；**Switch** 和 **Segmented control** 页面展示独立控件。

## 弹出面板

`ModernFlyout` 可容纳任意 `QWidget`，包括表单、开关和组合框。打开操作不阻塞；点击外部或按 Escape 关闭，重新打开时内容值仍保留：

```python
from PySide6.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QWidget
from pyside6_modern_widgets import ModernFlyout

button = QPushButton("Quick settings", window)
flyout = ModernFlyout(window)
content = QWidget()
layout = QVBoxLayout(content)
layout.addWidget(QLineEdit("Workspace name"))
flyout.setContentWidget(content)
button.clicked.connect(lambda: flyout.popup(button))
```

`popup(anchor, placement="bottom", gap=8)` 要求锚点可见。方向可选 `bottom`、`top`、`left`、`right` 或 `FlyoutPlacement` 枚举；空间不足时会尝试其他方向，并保持在锚点屏幕的可用区域内。过长内容会出现滚动条。锚点移动或缩放时面板重新定位；锚点隐藏、销毁或重新挂接时面板关闭。嵌套菜单或组合框的 Escape 会先关闭内部弹出层。

`setContentWidget()` 接管内容所有权并删除旧内容；`takeContentWidget()` 移出内容并将所有权交还调用者。`opened` / `closed` 报告可见性变化。面板优先继承锚点主题；Windows 11 上可使用 acrylic，Windows 10 和 macOS 使用不透明圆角表面。

## 通知

`NotificationManager` 在桌面或宿主窗口内显示通知卡片，不抢占键盘焦点。`notify()` 与 `post()` 每次都创建新的通知生命周期并返回 `NotificationHandle`。保存 handle 才能更新或关闭对应通知；已关闭的 handle 不会重新生效。

```python
from pyside6_modern_widgets import NotificationAction, NotificationManager

notifications = NotificationManager(window)
notifications.notify("Export complete", "Your report is ready.", kind="success")

job = notifications.notify(
    "Downloading",
    "Starting...",
    timeout_ms=None,
    progress=0,
    actions=[NotificationAction("cancel", "Cancel")],
)
job.update(message="Downloading... 65%", progress=65)
job.update(
    title="Download complete",
    message="Your file is ready.",
    kind="success",
    progress=None,
    actions=[NotificationAction("open", "Open file")],
    timeout_ms=5000,
)
notifications.actionTriggered.connect(lambda handle, action_id: print(handle.id(), action_id))
```

`update()` 只修改显式传入的字段。`progress=None` 隐藏进度，`icon=None` 恢复类型图标，`actions=[]` 删除操作。显式更新 `timeout_ms` 会重新开始倒计时；其他内容更新保留剩余时间。`timeout_ms=None` 表示常驻，正整数以毫秒为单位，`0` 无效。类型可用 `info`、`success`、`warning`、`error` 或 `NotificationKind`。标题和正文按纯文本处理；进度接受 0-100、忙碌状态 `-1` 或 `None`，达到 100 不会自动关闭。

操作是不可变的 `NotificationAction(id, text, close_on_trigger=True)`。同一通知内的 ID 必须唯一且非空。设置 `close_on_trigger=False` 可在点击后保留卡片；要关闭时，`actionTriggered(handle, id)` 会先于关闭信号发出。

| 构造选项 | 默认值和行为 |
| --- | --- |
| `position` | `NotificationPosition.BOTTOM_RIGHT`；支持四个角及 `"top-left"` 等字符串。 |
| `max_visible` | 每个屏幕最多 3 条，可用高度不足时可能更少。 |
| `capacity` | 最多接受 100 个生命周期，包括待投递、排队、可见、暂停及待 GUI 清理的通知。 |
| `width`、`margin`、`spacing` | 分别为 360、16、12 逻辑像素；卡片最高 360 像素。 |
| `default_timeout_ms` | 5000 毫秒；设为 `None` 可让默认通知常驻。 |
| `desktop` | Windows 和 macOS 默认桌面投递；传 `False` 强制窗口内投递。 |
| `theme`、`metrics` | 继承主题与默认 `ModernMetrics()`；动画时长可设为 0。 |

超过 `capacity` 时，提交方收到 `OverflowError`，已有通知不会被逐出。每个屏幕按先进先出投递，最早可见的卡片靠近所选角。`setScreen()` 指定默认目标屏幕，`notify(screen=...)` 可固定单条通知的屏幕；屏幕移除或 DPI/几何变化时会重新排列。`setPosition()`、`setMaxVisible()` 和 `setDeliveryPaused()` 可在运行时改变布局与投递。暂停投递或窗口隐藏时，已接受通知及倒计时都会保留。

超时从首次显示开始，悬停、窗口内操作获得键盘焦点或手动 `pauseTimeout()` 时暂停。`handle.snapshot()` 返回不可变的 `NotificationSnapshot`，即使关闭后仍可读取。`state()`、`isClosed()` 和 `closeReason()` 提供快捷查询。生命周期依次可能处于 `PENDING`、`QUEUED`、`VISIBLE`、`SUSPENDED`、`CLOSED`；`CLOSED` 是终态。`notifications()` 返回所有仍存活 handle 的有序元组，可用 `NotificationState` 过滤。`clear()` 关闭当前已接受的所有通知，但不阻止后续提交。

在 `QApplication` 的 GUI 线程创建管理器并调用 `notify()`、布局/主题 setter 和 `handle.widget()`。工作线程可以调用 `post()`、其余 handle 方法、`clear()` 与 `notifications()`；工作线程更新异步送达 GUI，相邻更新可能合并。管理器信号都在 GUI 线程发出：

| 信号 | 含义 |
| --- | --- |
| `notificationShown(handle)` | 首次显示。 |
| `notificationClosed(handle, reason)` | 生命周期结束；原因包括 `dismissed`、`expired`、`action`、`cleared`、`destroyed` 和 `failed`。 |
| `actionTriggered(handle, action_id)` | 用户点击操作。 |
| `notificationActivated(handle)` | 用户点击卡片正文，不自动关闭。 |
| `countChanged(visible, waiting, suspended)` | 数量变化；`waiting` 包括待投递和排队。 |
| `deliveryFailed(handle, message)` | 投递失败，handle 以 `failed` 关闭。 |

`handle.widget()` 仅借用已创建的 `ModernNotification` 视图；内容修改应使用 `handle.update()`，不要重新挂接或手动显示、隐藏受管理的卡片。单独创建的 `ModernNotification` 仍保留自身 setter 和 `addActionButton()`。桌面通知只在应用运行时存在，不进入系统通知中心，也不会自动遵循勿扰设置。

导航示例的 **Notifications** 页面展示类型、角落、队列、进度、操作和暂停投递。旧 ID API 到 Handle API 的对照见[0.6.0 迁移指南](docs/migration-0.6.md)。

## 窗口、菜单与标签页

`ModernWindow` 是基于 `QWidget` 的顶层窗口。它提供常用的 `QMainWindow` 风格 `menuBar()`、`addToolBar()`、`statusBar()` 和 `setCentralWidget()`，但不实现 `QMainWindow` 的停靠或状态管理功能。也可直接在窗口上安装布局；这两种布局方式不能在同一窗口混用。

```python
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QLabel
from pyside6_modern_widgets import ModernWindow

app = QApplication([])
app.setStyle("Fusion")
window = ModernWindow()
window.setWindowTitle("Modern window")

file_menu = window.menuBar().addMenu("&File")
exit_action = QAction("Exit", window)
exit_action.triggered.connect(window.close)
file_menu.addAction(exit_action)

window.setCentralWidget(QLabel("Hello"))
window.resize(800, 500)
window.show()
app.exec()
```

`menuBar()` 返回 `ModernMenuBar`，其下拉菜单和子菜单使用 `ModernMenu`。标题栏空间不足时，溢出按钮也使用相同菜单。手动创建菜单栏时，可用 `window.titleBar.addCustomWidget(menu_bar, align="left")` 将其放入标题栏。`ModernMenu` 接受常见 `QMenu` 构造方式，支持 `QAction`、分隔线、可勾选操作和子菜单。

`ModernToolBar` 保留 `QToolBar` 的操作、方向、图标尺寸和工具按钮接口。`window.addToolBar("Tools")` 也会创建 `ModernToolBar`。溢出菜单保留隐藏操作的快捷键、启用/勾选状态和子菜单；`addWidget()` 的控件不会被复制进溢出菜单。`overflowButton()` 和 `overflowMenu()` 可供访问，但溢出菜单内容由工具栏管理。Windows 11 可为菜单启用 acrylic。

`ModernPushButton` 与 `ModernToolButton` 保留 Qt 原生动作、快捷键、焦点、菜单和信号语义，并用主题绘制状态。`ModernToolButton` 支持五种 `toolButtonStyle`、四方向箭头、`setAutoRaise()` 和三种弹出模式。用法与 Fusion 尺寸对照见 [ModernPushButton](docs/modern-push-button.md) 和 [ModernToolButton](docs/modern-tool-button.md) 文档。

`setTitleBarVisible(False)` 隐藏整个标题栏而不删除自定义控件，传 `True` 恢复；macOS 的原生窗口按钮也遵循该偏好。`setTitleVisible()` 只控制标题文字，`setIconVisible()` 只控制标题栏图标，`setTitleAlignment("center")` 可将文字居中。设置保持原始窗口标题和图标供操作系统使用。

现有顶层 `QWidget` 子类可以改为继承 `ModernWindow` 并继续直接安装布局。`setDragRegion(widget)` 让非交互内容区域触发系统窗口移动；传入第二个参数 `False` 可取消。Windows 上跨不同 DPI 显示器移动时会尽量保持窗口逻辑尺寸。

`centralWidget()` 读取中心组件，`takeCentralWidget()` 移出并转交所有权；`setCentralWidget()` 替换时删除旧的受管理组件。`NavigationView`、`TabView` 和 `ModernTabWidget` 的 `removePage()` / `removeTab()` 会隐藏并移除页面，但保留 Qt 父对象；需要接管页面时使用 `takePage()` / `takeTab()`。`NavigationSidebar.removeItem()` 同样保留按钮父对象，`takeItem()` 才转移所有权。无效索引不改变状态。

`ModernDialog` 保留 `QDialog` 的布局、`exec()`、`accept()`、`reject()` 和结果代码。`ModernMessageBox` 保留 `QMessageBox` 的标准按钮、详细文本、复选框、默认/退出按钮、返回值和完成信号，同时使用主题外观：

`ModernDialog` 的内容按钮可使用 `ModernPushButton`，通过 `QDialogButtonBox.addButton()` 指定按钮角色。`ModernMessageBox` 的标准、自定义和详情按钮共用现代按钮的绘制逻辑，保留原有 Qt 按钮对象及标准按钮映射。

```python
from pyside6_modern_widgets import ModernMessageBox

answer = ModernMessageBox.question(
    window,
    "Confirm",
    "Continue with this operation?",
    ModernMessageBox.StandardButton.Yes | ModernMessageBox.StandardButton.No,
    ModernMessageBox.StandardButton.No,
)
```

`ModernTabWidget` 适合固定页面，不提供文档标签页的添加、关闭和拖动交互。`TabView` 提供这些交互以及 `Ctrl+T`、`Ctrl+W`、`Ctrl+Tab`、`Ctrl+Shift+Tab` 快捷键。`TabView.addTab()` 使用 Qt 参数顺序：`addTab(widget, text)` 或 `addTab(widget, icon, text)`；`insertTab()` 的负索引与 `QTabWidget` 一样表示追加。程序可以选中禁用页，但用户导航和 `nextTab()` / `previousTab()` 会跳过禁用页。

`NavigationView` 会在展开侧栏导致当前页面宽度低于最小宽度时自动使用覆盖模式。需要自定义响应式策略时，可调用 `setAutoSidebarOverlay(False)`，再用 `setSidebarOverlay()` 控制。`sidebar.button(index)` 返回借用按钮；对其调用 `setChecked(True)` 会同步当前索引与页面，并在选择变化时发出 `currentChanged`。`itemActivated` 只报告按钮激活，包括重复点击当前项。

## 主题

全局 `theme_manager()` 默认使用 **System 模式并启用壁纸颜色**。在创建 `QApplication` 后、创建窗口前选择模式。库不会修改应用的 Qt 样式；推荐设置 Fusion 以在 Windows 和 macOS 上获得一致的 palette 行为：

```python
from PySide6.QtWidgets import QApplication
from pyside6_modern_widgets import ModernWindow, ThemeMode, theme_manager

app = QApplication([])
app.setStyle("Fusion")
manager = theme_manager()
manager.setMode(ThemeMode.SYSTEM)  # 也可选择 LIGHT 或 DARK。
manager.setWallpaperEnabled(False)  # 可选：使用基础主题颜色。
window = ModernWindow()
window.show()
app.exec()
```

| 管理器 API | 作用 |
| --- | --- |
| `setMode()` / `mode()` | 选择并读取用户偏好的 System、Light 或 Dark 模式。 |
| `isDark()` / `theme()` | 读取实际明暗模式及不可变的 `ModernTheme` token。 |
| `setThemes(light=..., dark=...)` | 替换两套基础主题，不更改模式和壁纸策略。 |
| `setWallpaperEnabled()` / `wallpaperEnabled()` | 控制是否从壁纸提取颜色。 |
| `refreshWallpaperTheme()` | 异步请求刷新；壁纸颜色关闭时无效。 |
| `modeChanged`、`themeChanged`、`wallpaperEnabledChanged` | 分别报告偏好、有效主题及壁纸策略变化。 |

System 模式监听 `QApplication.styleHints().colorScheme()`；未知系统明暗设置回退到 Light。固定 Light/Dark 模式不会因系统变化而立即改变外观，但切回 System 时会使用最新系统设置。重复设置相同有效状态不会重复发信号。管理器接管应用 palette 的语义颜色角色，不安装全局样式表，也不会自动保存偏好。

可用 `dataclasses.replace()` 自定义基础主题。`accent` 和 `on_accent` 默认为 `None`，此时继承 Qt 的系统 Accent、Highlight 和相关文字颜色；设置字符串可显式覆盖。启用壁纸颜色时，管理器从壁纸派生 `focus`、`watercolor_base` 和 `watercolor_spots`，其他基础 token 保持不变。壁纸不可用时使用基础主题；发现、采样和刷新在 GUI 线程外进行。

`ModernWindow`、`ModernDialog` 和 `NavigationSidebar` 覆盖层接受 `watercolor=False`，也可通过 `setWatercolorEnabled()` / `isWatercolorEnabled()` 切换为主题的纯色 `surface_alternate`。这与壁纸颜色采样是两项不同设置；导航示例只在启用水彩背景时允许修改壁纸颜色开关。窗口失活时使用纯色背景，重新激活后以 250 毫秒渐变恢复效果。

Windows 11 的 acrylic 可按组件关闭。`ModernMenu`、`ModernComboBox`、`ModernFontComboBox`、`ModernFlyout`、`ModernNotification`、`NotificationManager`、`ModernMenuBar` 和 `ModernToolBar` 接受 `acrylic=False`，并提供 `setAcrylicEnabled()` / `isAcrylicEnabled()`。默认启用；原生 acrylic 不可用时使用不透明表面。已有可见弹出层和通知会立即更新，子菜单、工具栏溢出菜单和受管理通知继承所有者设置。

```python
menu = ModernMenu(acrylic=False)
combo = ModernComboBox(acrylic=False)
notifications = NotificationManager(window, acrylic=False)
menu.setAcrylicEnabled(True)
```

提供 `theme()` / `setTheme()` 的组件依次采用**本地显式主题、最近的主题祖先、全局管理器**。`setTheme(None)` 恢复继承；隐藏控件或重新挂接父对象时也会更新。Flyout 优先继承锚点主题，受管理通知卡片继承管理器主题。有效主题应用后才发出 `themeChanged(theme)`。普通 Qt 控件继续继承应用或父控件的 palette；显式 palette 和写死颜色的 QSS 可能覆盖它。

```python
window.setTheme(DARK_THEME)
child.setTheme(LIGHT_THEME)
child.setTheme(None)  # 恢复继承 window 的主题。
```

应用可用 `QSettings` 保存用户选择的 `ThemeMode`，不要保存 System 模式当时解析出的明暗结果。完整的自定义主题、palette、壁纸监控和偏好保存示例见[英文说明](README.md#themes)。

## 示例与资源

运行 `python examples/navigation_view_example.py` 打开控件对照示例；`python examples/tab_view_example.py` 展示文档标签页；`python examples/edge_dock_example.py` 展示边缘停靠。示例说明位于 [`examples/README.md`](examples/README.md)。库附带的窗口和导航图标来自 [Icons8](https://icons8.com)，受 Icons8 许可约束。
