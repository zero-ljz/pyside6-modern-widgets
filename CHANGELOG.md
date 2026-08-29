# Changelog

All notable changes to this project are documented in this file.

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

[0.4.0]: https://github.com/zero-ljz/pyside6-modern-widgets/compare/v0.3.3...v0.4.0
