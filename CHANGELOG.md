# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

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

### Changed

- Deferred wallpaper discovery and color extraction until the global theme is
  first used, keeping package imports free of wallpaper I/O and external
  process calls.
- Removed window theme switching and the standard and classic surfaces. The
  remaining modern surface now follows desktop-wallpaper colors automatically,
  using low-frequency metadata checks and file notifications.
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
  state while the default Windows procedure owns activation, moving, resizing,
  caption double-clicks, and system-command transitions.

### Fixed

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

[Unreleased]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.4.3...HEAD
[0.4.3]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.3.3...v0.4.0
