# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

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
