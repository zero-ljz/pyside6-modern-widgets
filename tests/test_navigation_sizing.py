"""Hidden navigation pages must not constrain native window resizing."""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QLabel, QLayout, QVBoxLayout, QWidget

from pyside6_modern_widgets import ModernWindow, NavigationView

_APP = QApplication.instance() or QApplication([])


def test_hidden_page_height_for_width_does_not_enlarge_window():
    window = ModernWindow()
    view = NavigationView()
    window.setCentralWidget(view)
    home = QWidget()
    home_layout = QVBoxLayout(home)
    description = QLabel("Home description that can wrap onto multiple lines.")
    description.setWordWrap(True)
    home_layout.addWidget(description)
    home_layout.addStretch()
    view.addPage(home, "Home")
    window.resize(1000, 640)
    window.show()
    _APP.processEvents()
    # Qt's Windows backend checks the target physical rectangle while the
    # source DPR can still be 1.75: 1000 x 640 becomes 571 x 366 here.
    proposed = QSize(571, 366)
    before = QLayout.closestAcceptableSize(window, proposed)

    tall = QWidget()
    tall_layout = QVBoxLayout(tall)
    for index in range(30):
        label = QLabel(f"Hidden row {index}: text with width-dependent height.")
        label.setWordWrap(True)
        tall_layout.addWidget(label)
    view.addPage(tall, "Tall")
    _APP.processEvents()
    try:
        assert QLayout.closestAcceptableSize(window, proposed) == before
        view.setCurrentIndex(1)
        _APP.processEvents()
        assert QLayout.closestAcceptableSize(window, proposed).height() > before.height()
        view.setCurrentIndex(0)
        _APP.processEvents()
        assert QLayout.closestAcceptableSize(window, proposed) == before
    finally:
        window.close()
        window.deleteLater()


def test_height_for_width_follows_current_page_and_empty_stack():
    view = NavigationView()
    stack = view.stackedWidget
    assert not stack.hasHeightForWidth()
    assert stack.heightForWidth(200) == -1
    fixed = QWidget()
    view.addPage(fixed, "Fixed")
    wrapped = QLabel("Wrapping text " * 20)
    wrapped.setWordWrap(True)
    view.addPage(wrapped, "Wrapped")
    assert not stack.hasHeightForWidth()
    view.setCurrentIndex(1)
    assert stack.hasHeightForWidth()
    assert stack.heightForWidth(200) > stack.heightForWidth(400)
    view.removePage(1)
    assert not stack.hasHeightForWidth()
    view.removePage(0)
    assert stack.heightForWidth(200) == -1
    view.deleteLater()
    fixed.deleteLater()
    wrapped.deleteLater()
