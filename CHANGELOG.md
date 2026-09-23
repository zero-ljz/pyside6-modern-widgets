# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [0.5.13] - 2026-09-23

### Added

- Add `ModernTabWidget` for compact, fixed application sections while preserving
  the native `QTabWidget` API and keyboard behavior.
- Add `ModernSegmentedControl` with exclusive indexed Qt buttons, compact sizing,
  inherited or locally overridden themes, and selected/hover/disabled states;
  demonstrate it in the navigation gallery.

### Fixed

- Restore native macOS full-size and transparent title-bar settings when AppKit
  resets them during window updates, preventing a separate white title strip.
- Realign macOS traffic lights immediately and after native title changes so
  switching images does not flash the zoom button at AppKit's default position.

## [0.5.12] - 2026-09-22

### Added

- Add visible Home and search controls to the navigation example custom title
  bar to exercise macOS safe-area layout.

### Fixed

- Prevent Qt macOS safe-area insets from shifting custom title-bar widgets below
  the transparent full-size content view.

## [0.5.11] - 2026-09-22

### Added

- Add `EdgeDockController`, `DockConfig`, and `DockSide` for optional screen-edge
  snapping and auto-hide, with explicit drag surfaces, customizable gray restore
  handles, multi-screen work areas, off-screen release recovery, and lifecycle cleanup.
- Add Qt Linguist-based internationalization for library-owned UI text, including
  a bundled Simplified Chinese catalog, runtime language-change handling, and the
  public `load_translator()` catalog loader.
- Add complete English and Simplified Chinese catalogs to both runnable examples,
  including Qt standard dialog translations selected from the system locale.

### Changed

- Use the native transparent macOS title bar and system traffic-light controls
  for `ModernWindow`, while retaining themed title content and custom widgets.
  Center the traffic lights vertically and use the same inset at the left edge.
- Reduce the default `ModernSwitch` track to 32 by 16 logical pixels and its
  minimum height to 20 pixels so it aligns better with native form controls.
- Match the closed `ModernComboBox` height to the current native Qt combo-box
  height without changing its modern popup row spacing.
- Replace the solid overflow triangles in long `ModernComboBox` popups with
  outlined up and down chevrons.

### Fixed

- Reapply macOS traffic-light positions on native window resize notifications,
  covering green-button layout changes that do not emit a view-frame notification.
- Delegate edge-dock dragging to the shared native system-move path, preserving
  mixed-DPI window sizing. Defer snapping until native movement finishes and
  check live Windows button state when Qt does not receive the mouse release.
- Keep centered title text at its intended height after a macOS full-screen
  transition temporarily compresses the title-bar layout spacer.
- Keep macOS traffic lights centered during live resizing using synchronous
  native frame notifications, with cleanup when the native window is destroyed.
- Restore the transparent macOS title bar after showing or hiding a toolbar,
  preventing the native title-bar material from turning white on toolbar pages.
- Preserve Qt's macOS message-box content margins and use a draggable native
  title bar, preventing clipped content and buttons.
- Keep hidden navigation pages out of height-for-width calculations, preventing
  the Home page from making the window taller during mixed-DPI monitor drags.
- Suppress native radio bullets when pressing or switching exclusive `ModernMenu`
  items so only clean modern check marks are shown.

## [0.5.10] - 2026-09-18

### Changed

- Give `ModernComboBox` WinUI-style translucent control fills for light/dark themes
  and normal, hover, pressed and disabled states, including its default editable
  field, while retaining crisp text and arrows and the existing popup surface.

### Fixed

- Preserve title-bar control hover after dismissing a popup menu over native
  caption, maximize or resize regions.
- Share the native and portable system-window menu across `ModernWindow`,
  `ModernDialog` and `ModernMessageBox`, including right-clicks across the full
  title bar. Use the alternate surface palette for modern message boxes.
- Prevent low-to-high DPI monitor moves from widening windows before
  `WM_DPICHANGED` by keeping speculative minimum and maximum tracking bounds
  permissive across both the source and target scales.

## [0.5.9] - 2026-09-18

### Removed

- Remove the default `ModernWindow` title-bar More menu and its button, including
  the built-in application exit action and confirmation dialog.

### Added

- Add `ModernWindow.setDragRegion()` and `startSystemMove()` so tool content can
  use native cross-monitor movement with a portable fallback.
- Add `ModernToolBar` with native toolbar geometry, themed controls, a `ModernMenu` popup,
  shared Qt actions and widget-action factories, horizontal/vertical and RTL
  layouts, theme inheritance and local overrides. Include a Toolbar gallery
  page. `ModernWindow.addToolBar(title)` now creates this modern toolbar.

### Fixed

- Restore minimized maximized windows reliably on Windows. Do not reapply
  `WS_MAXIMIZE` while minimized: Qt retains `WindowMaximized` only as the restore
  target. Standard Qt restore calls now recover the native window and preserve
  its maximized state and normal geometry without application workarounds.
- Apply native mixed-DPI tracking and size constraints to `Qt.Tool` modern
  windows without changing their taskbar, Alt+Tab or native-frame semantics.
- Apply shared mixed-DPI size constraints during `WM_GETDPISCALEDSIZE`, before
  `WM_DPICHANGED`, so an early minimum-size query cannot enlarge a window,
  dialog or message box using the previous monitor's scale. Discard speculative
  sizing on drag cancellation and avoid compounding repeated DPI queries.
- Keep checked menu-icon backgrounds translucent instead of drawing opaque
  native button panels on acrylic menus.
- Use equal padding on all four sides of the window title bar.

## [0.5.8] - 2026-09-16

### Added

- Add `ModernNotification`, `NotificationManager`, `NotificationKind`, and
  `NotificationPosition`: non-activating desktop notifications, per-screen FIFO
  stacks and bounded queues, timed/persistent delivery, hover/focus/manual pause,
  actions, progress and ID-based updates, thread-safe posting, screen-change
  handling, animated placement, theme inheritance, and Windows 11 acrylic.
  Include in-window delivery with automatic Wayland fallback, lifecycle cleanup,
  and an interactive Notifications gallery page.
- Add `ModernFlyout` and `FlyoutPlacement` for non-blocking anchored panels with
  arbitrary widget content, four preferred sides, screen-edge fallback, scrolling,
  native popup dismissal and keyboard focus, inherited/local themes, and Windows
  11 acrylic with an opaque fallback. Include a Flyout page in the navigation gallery.

## [0.5.7] - 2026-09-16

### Changed

- Show switch focus outlines only during keyboard interaction, hiding them on
  mouse clicks. Consolidate the switch and combo box demos into dedicated pages
  of the navigation example and remove the standalone examples.

### Added

- Add `ModernSwitch` with an animated thumb, system accent colors, native checkbox
  signals and keyboard input, theme inheritance, disabled/RTL states, and a
  compact track and room for large-font labels. Include a comparison example.

### Fixed

- Preserve the active accent and thumb contrast for checked switches when their
  window loses activation; disabled controls still use the disabled colors.
- Keep combo popup rows transparent under application style sheets, preserving
  Windows acrylic instead of covering it with opaque menu-item backgrounds.
- Guard combo event filters during base construction and keep switch tracks at
  36 by 18 logical pixels independently of font and unrelated form-control QSS.

## [0.5.6] - 2026-09-15

### Changed

- Share edge resizing between windows and dialogs, chrome styling/layout across
  windows, dialogs and message boxes, native DWM corner calls across windows and
  popups, and ancestor theme lookup between menu bars and combo boxes.
- Match editable default-list row heights to ordinary modern combo rows and add
  8 logical pixels of horizontal padding per side and 2 pixels above/below the
  list, without changing closed controls.
- Use four square corners for editable combo controls and popups, with Windows 11
  acrylic on the popup. Non-editable combos retain rounded corners.

### Added

- Add `ModernComboBox`, a `QComboBox` subclass with rounded
  controls, full focus borders and a popup sharing `ModernMenu`'s Windows 11
  acrylic, rounded surface and selection styling. Preserve Qt's popup container,
  models, delegates, signals, editing and input handling, with inherited or local themes.
- Add a native/modern combo box comparison example and behavior regression tests.

### Fixed

- Apply the shared mixed-DPI protection to `ModernMessageBox`, including native
  size constraints after expanding or collapsing detailed text.
- Prevent `ModernDialog` from growing when dragged between Windows monitors with
  different DPI scales. Use the target DPI for native minimum/maximum sizing,
  including rapid boundary reversals. Share DPI tracking, Qt scale rounding and
  native size constraints with `ModernWindow` through one internal implementation.
- Preserve caller-supplied combo palettes and list configuration through opening
  and theme changes. Honor native frameless rendering and Qt's expanded-state flag.
- Match native Fusion combo box focus-border timing and palette-derived system
  highlight colors, including the different editable and non-editable behavior.
- Prevent black flashes when opening editable modern combo boxes by skipping Qt's
  screenshot-based popup animation, which cannot capture the acrylic backdrop.
  Restore the application's animation preference immediately after opening.

## [0.5.5] - 2026-09-13

### Fixed

- Preserve inactive title text and icon opacity when the application uses global
  QSS, including selectors that only target unrelated labels.
- Restore inactive title and menu foregrounds through Qt's `Inactive` palette
  group, with 50% alpha. Title-bar icons follow that group while retaining native
  button rendering; remove foreground activation monitors and dynamic menu QSS.
- Restore visible Win11 menu acrylic after theme palette propagation changed
  the native tint to pure white. Limit very light acrylic tints without changing
  the Qt surface or the opaque fallback, including for open menus and submenus.
- Restore native Qt system accent and selection roles by default, including after
  switching back from custom colors. Built-in `accent`/`on_accent` are `None` for
  inheritance; explicit custom colors still override them.
- Hide the title-bar pin button on native Wayland, where Qt's standard shell
  integration does not support always-on-top.
- Synchronize native Windows maximize state before updating the restore tooltip.

### Changed

- Replace the global theme API with `ThemeMode.SYSTEM/LIGHT/DARK`, `setMode()`,
  `mode()`, `isDark()`, `setThemes(light=..., dark=...)`, and `modeChanged`.
  Remove manager-level `setTheme()`, `setFollowsSystemTheme()`, and
  `followsSystemTheme()` without compatibility aliases; retain widget overrides.
- Default to System mode and detect OS appearance through Qt style hints instead
  of reading the library's application palette. Unknown schemes use Light.
- Make wallpaper accents an independent setting with `setWallpaperEnabled()`,
  `wallpaperEnabled()`, and `wallpaperEnabledChanged`. Disabling restores base
  colors and invalidates in-flight samples; custom base pairs survive switching.
- Complete native Qt palette roles, including selection, disabled backgrounds,
  placeholders, tooltips, and links; export `palette_for_theme()` for custom pages.
- Refresh visible menu acrylic tints after palette changes and propagate owner
  palettes to submenus. Add live appearance controls to the navigation example.

## [0.5.4] - 2026-09-13

### Changed

- Make `ModernMessageBox` inherit directly from `QMessageBox`, retaining its
  native content layout, buttons, keyboard handling, results, and signals while
  preserving themed frameless chrome. Custom button return codes and ownership
  now follow Qt instead of the former `ModernDialog` implementation.

### Fixed

- Release the cached central-widget reference when its ownership moves away
  from a `ModernWindow`, preventing later replacements from deleting another
  window's content.
- Move wallpaper discovery, metadata checks, and image sampling off the GUI
  thread. Coalesce refresh requests, avoid repeated discovery after a missing
  wallpaper, and ignore stale results after a manual theme selection.
- Keep tab labels and pages synchronized when inserting an existing page again,
  and disable the page content along with its tab.
- Scope tab shortcuts to the nearest focused tab view, including nested views, preserving
  platform-specific standard key bindings.
- Keep built-in title-bar controls out of the tab order in windows, dialogs,
  and message boxes, and prevent them from becoming dialog default buttons.
  Custom title-bar widgets retain their own keyboard focus policies.
- Apply the Windows restore handling to `setWindowState(WindowNoState)` as well
  as `showNormal()`, preserving geometry and keeping hidden windows hidden.
- Remove tab and navigation entries when their pages are destroyed or reparented,
  and publish selection changes only after the entries and pages are synchronized.
- Emit `TabView.currentChanged` when the first tab becomes current.
- Toggle Windows always-on-top status without hiding/re-showing the window or
  briefly exposing the system frame.
- Restore maximized Windows windows to their original size before title-bar
  dragging, including after minimizing/restoring or hiding/showing the window.
  Clear the native maximize state before handing the drag back to Windows.

## [0.5.3] - 2026-09-11

### Fixed

- Kept transparent Windows acrylic menu surfaces in native mouse hit testing,
  so blank space across the full width of a menu item now receives hover input.

## [0.5.2] - 2026-09-11

### Fixed

- Prevented windows at their minimum size from growing when dragged between
  Windows monitors with different DPI scales. Size constraints now use the
  destination DPI during the transition, preserving Qt's scale rounding policy
  and global scale multiplier.

## [0.5.1] - 2026-09-11

### Changed

- Temporarily replace wallpaper-colored backgrounds with `#F3F3F3` in light
  themes or the theme's surface color in dark themes while windows are inactive,
  with a 250 ms linear fade in both directions that continues from the current
  blend when focus changes mid-animation.
  This also applies to dialogs, message boxes, and navigation sidebar overlays.

## [0.5.0] - 2026-09-11

### Added

- Added `ModernDialog`, a frameless `QDialog` that shares the modern window
  chrome while retaining native dialog layouts, modality, signals, and results.
- Added `ModernMessageBox` with common `QMessageBox` icons, standard and custom
  buttons, convenience methods, detailed text, and optional checkboxes.
- Added `ModernMenu`, a `QMenu` subclass with Windows 11 system acrylic, an
  opaque fallback, and rounded backgrounds while retaining
  native menu layout.
- Added `ModernMenuBar`, which creates `ModernMenu` drop-down menus while
  preserving the standard `QMenuBar` API.
- Added independent title text and icon visibility controls to `ModernWindow`
  and its title bar, with getters that retain the configured state while hidden.
- Added left and centered title alignment, keeping centered text clear of
  custom title-bar widgets and window buttons in narrow windows.
- Added `theme_from_wallpaper()` for deriving a modern theme from wallpaper.

### Changed

- Deferred wallpaper discovery and color extraction until the global theme is
  first used, keeping package imports free of wallpaper I/O and external
  process calls.
- Removed window theme switching and the standard and classic surfaces. The
  remaining modern surface now follows desktop-wallpaper colors automatically,
  using low-frequency metadata checks and file notifications.
- Removed the legacy `WatercolorStyle`, `theme_with_watercolor_style`,
  `ORIGINAL_LIGHT_THEME`, and `ORIGINAL_DARK_THEME` exports.
- Made `ModernWindow` use modern menus for its menu bar, title-bar menu, and
  cross-platform system-menu fallback.
- Made `ModernWindow` accept the `QWidget(parent, f)` constructor shape and
  direct widget layouts, while synchronizing its custom chrome with tool and
  popup window flags.
- Reduced the default expanded navigation sidebar width from 240 to 224 logical
  pixels for a more compact desktop layout.
- Made automatic navigation overlay mode follow the current page's minimum
  width instead of fixed `NavigationView` width breakpoints, while restoring
  the user's sidebar toggle intent when returning to side-by-side mode.
- Extracted reusable window surfaces, overlays, and title-bar behavior from
  `ModernWindow` for use by other top-level widgets.
- Reworked the Windows frameless-window boundary so Qt exclusively owns window
  state while Windows supplies native activation, moving, resizing, and hit
  testing. Caption double-clicks and maximize/restore system commands now route
  through Qt to preserve the saved normal geometry.
- Styled manually created `ModernMenuBar` instances with transparent backgrounds
  and rounded selection highlights that follow their containing window's theme
  or the global theme when used on their own.
- Made menu-bar overflow use `ModernMenu` while retaining Qt action updates.
- Updated the navigation example with a title-bar menu bar and hidden title text.

### Fixed

- Preserved normal window geometry when mixing title-bar double-clicks, native
  system commands, and custom maximize/restore buttons, and retained maximized
  state when restoring a minimized maximized window.
- Kept blank title-bar space draggable beside embedded menus with either title
  alignment and with title text hidden.
- Made maximized title-bar dragging use the native Windows maximize state when
  Qt state updates lag, and restored rounded corners immediately on drag-restore.
- Kept the cursor anchored to the same title-bar position when dragging a
  maximized `ModernWindow` back to its restored size.
- Consumed native Windows maximize-button press and release messages in the
  custom title bar, preventing a fallback system button from appearing and
  ensuring the visible maximize control performs maximize and restore itself.
- Cleared and repainted the complete Windows backing surface after display
  resolution, work-area, or DPI changes, preventing stale title-bar button
  pixels after the window geometry is recomputed.
- Kept fixed-size and partially constrained windows from exposing native or
  custom maximize actions, and resynchronized Win32 frame capabilities when
  minimum or maximum sizes change at runtime.
- Removed rounded transparent corners and resize hit targets while modern
  windows and dialogs are full screen.
- Kept `ModernDialog` frameless chrome synchronized after window-flag changes
  and accepted the standard `(parent, flags)` constructor form.
- Made cached menu bars, status bars, and central widgets recover safely after
  external deletion, and allowed `setCentralWidget(None)` to clear content.
- Added manual window move and resize fallbacks when a non-Wayland Qt platform
  plugin declines the native system operation.
- Kept the native and fallback system menus aligned with each window's resize,
  minimize, maximize, and close capabilities.
- Kept the title-bar pin button synchronized with externally supplied
  `WindowStaysOnTopHint` flags.
- Emitted navigation item activation only for user interaction and prevented
  duplicate activation while removing the current page.
- Restored clean type checking for the package's inline `py.typed` annotations.
- Restored complete native Windows styles for `ModernWindow`, including the
  system menu and minimize, maximize, and resize capabilities, while keeping
  the standard caption outside the client area.
- Restored native Windows dragging, edge resizing, Aero Snap, and Windows 11
  Snap Layouts through non-client hit testing instead of synthetic move and
  maximize commands.
- Restored custom maximize-button hover feedback during native Windows
  non-client interactions.
- Kept native system-menu placement and hit testing stable across mixed-DPI
  monitors by converting through the HWND's physical client geometry.
- Positioned the native system menu's Move command at the horizontal and
  vertical center of the custom title bar instead of the removed native frame.
- Removed delayed logical-size restoration after mixed-DPI screen changes so
  Qt and Windows can complete their native DPI transition without a competing
  resize.
- Unified the top-level surface policy used by `ModernWindow`, `ModernDialog`,
  and `ModernMessageBox`: Windows 10 uses opaque square corners to preserve
  responsive updates without translucent resize flicker, while Windows 11
  keeps native DWM rounding.
- Prevented menu-bar style sheets from overriding `ModernMenu` palette and
  drawing behavior in `ModernMenuBar` drop-downs.
- Matched the native Windows acrylic backdrop to rounded menu corners and made
  its tint more transparent, with a Qt-painted fallback when unavailable.
- Kept runtime navigation item text updates synchronized across expanded and
  collapsed states, including updates made through the exposed item button.
- Restored the user's expanded sidebar intent after window chrome actions or
  resizing move an overlay sidebar back into a side-by-side layout.

## [0.4.3] - 2026-08-30

### Changed

- Restored the original navigation item active geometry in both collapsed and
  expanded sidebars while keeping the toggle and outer spacing aligned with
  the navigation list.

## [0.4.2] - 2026-08-30

### Fixed

- Matched collapsed navigation selections and the pane toggle background to
  WinUI's 40-by-36 logical-pixel size and 4-pixel list and edge rhythm while
  keeping expanded right corners visible beside the scrollbar.

## [0.4.1] - 2026-08-30

### Fixed

- Kept collapsed navigation selection backgrounds square and centered while
  allowing the vertical scrollbar to overlay their right edge.
- Prevented windows hosting navigation views from resizing below the height
  required by fixed bottom sidebar items.

### Changed

- Tightened the vertical spacing between sidebar navigation items.
- Reduced the initial tooltip delay for collapsed sidebar navigation items.
- Restored vertical scrolling when collapsed sidebar navigation items overflow.
- Rounded the right corners of expanded overlay sidebars in narrow layouts.
- Removed the expanded overlay sidebar's right-edge shadow.
- Outlined the top, right, and bottom of expanded overlay sidebars with the window border color.

## [0.4.0] - 2026-08-29

### Added

- Added an automatic responsive overlay mode to `NavigationView`, including
  hysteresis between compact and wide layouts and restoration of the user's
  sidebar expand/collapse intent.
- Added a watercolor surface, right-edge shadow, and outside-click dismissal
  for an expanded overlay sidebar.
- Added system-derived inactive title text colors for custom title bars.

### Changed

- Cached and reused watercolor surfaces during native live resizing to reduce
  flicker while preserving the watercolor appearance.
- Updated the navigation example to allow narrow resizing and demonstrate the
  automatic overlay behavior without application-specific resize code.
- Limited stacked navigation size hints to the current page so hidden pages do
  not impose their minimum dimensions on the window.

### Fixed

- Restored native rounded corners after maximizing and returning a window to
  its normal state on Windows.
- Restored the arrow cursor after a native resize when the pointer moves over
  content widgets created after window initialization.
- Stopped interrupted sidebar animations before applying an immediate width
  change, preventing stale animations from restoring the wrong width.
- Refreshed item views through `QWidget.update(widget)` so `QTableWidget` does
  not resolve its incompatible overload.
- Kept overlay expansion from moving content or increasing the top-level
  window width.

[Unreleased]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.13...HEAD
[0.5.13]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.12...v0.5.13
[0.5.12]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.11...v0.5.12
[0.5.11]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.10...v0.5.11
[0.5.10]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.9...v0.5.10
[0.5.9]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.8...v0.5.9
[0.5.8]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.7...v0.5.8
[0.5.7]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.6...v0.5.7
[0.5.6]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.5...v0.5.6
[0.5.5]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.4...v0.5.5
[0.5.4]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.3...v0.5.4
[0.5.3]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.4.3...v0.5.0
[0.4.3]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.3.3...v0.4.0
