"""Floating HUD that lists active leader-mode bindings for the anchors plugin.

Ported from node_layout's overlay; the Win32 ctypes and Linux X11 hint
work-arounds are preserved verbatim because they were the difference
between a usable HUD and a flashing taskbar (see node_layout 260331-axc).

The bindings come from constants.LEADER_BINDINGS so this module and leader.py
share a single source of truth.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

import nuke

from constants import LEADER_BINDINGS


# ---------------------------------------------------------------------------
# Platform-specific activation suppression.
# Ported byte-for-byte from node_layout_overlay.py; see that file's header
# comments for why these dance steps are necessary.
# ---------------------------------------------------------------------------

def _apply_no_activate_win32(hwnd):
    """Set WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW on *hwnd* via raw Win32 API."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        current_ex_style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        new_ex_style = current_ex_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new_ex_style)
        user32.SetWindowPos(
            hwnd,
            0,
            0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
    except Exception:
        pass


def _apply_linux_hints(widget):
    """Set _NET_WM_STATE_SKIP_TASKBAR / _NET_WM_STATE_SKIP_PAGER on Linux."""
    if not sys.platform.startswith("linux"):
        return
    try:
        widget.setProperty("_NET_WM_STATE_SKIP_TASKBAR", True)
        widget.setProperty("_NET_WM_STATE_SKIP_PAGER", True)
    except Exception:
        pass


def _restore_nuke_focus(parent_widget):
    """Re-activate the Nuke parent window after show on Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        from PySide6.QtWidgets import QApplication

        focus_target = parent_widget
        if focus_target is None:
            focus_target = QApplication.activeWindow()
        if focus_target is None:
            return
        target_hwnd = int(focus_target.winId())
        ctypes.windll.user32.SetForegroundWindow(target_hwnd)  # type: ignore[attr-defined]
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

_INPUT_KEY_COLOR = QColor(60, 160, 80)        # Q W E R — set-input commands (green)
_CHAINING_KEY_COLOR = QColor(40, 120, 160)    # L — teal (stays armed; chain repeat)
_NEUTRAL_KEY_COLOR = QColor(220, 220, 220)    # F J Z X comma — neutral white
_DISABLED_COLOR = QColor(70, 70, 70)          # greyed-out cells

_INPUT_KEYS = frozenset({'Q', 'W', 'E', 'R'})
_CHAINING_KEYS = frozenset({'L'})


def _badge_color_for(letter):
    if letter in _INPUT_KEYS:
        return _INPUT_KEY_COLOR
    if letter in _CHAINING_KEYS:
        return _CHAINING_KEY_COLOR
    return _NEUTRAL_KEY_COLOR


def _rgb_string(color):
    return f"rgb({color.red()}, {color.green()}, {color.blue()})"


# ---------------------------------------------------------------------------
# Clickable key cell — keyboard and mouse share the dispatch path.
# ---------------------------------------------------------------------------

class ClickableKeyCell(QWidget):
    """Square key badge that dispatches the same action as pressing the key.

    *canonical_letter* is the QWERTY-canonical letter the binding is registered
    under (used for dispatch and for the badge-color heuristic so colours stay
    stable across layouts).  *display_letter* is what's actually printed on the
    user's physical key for the current keyboard layout.
    """

    def __init__(self, canonical_letter, display_letter, action_label, parent=None):
        super().__init__(parent)
        self._canonical_letter = canonical_letter
        self._enabled = True

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._badge_frame = QFrame()
        self._badge_frame.setFixedSize(70, 70)

        badge_inner_layout = QVBoxLayout(self._badge_frame)
        badge_inner_layout.setContentsMargins(3, 6, 3, 4)
        badge_inner_layout.setSpacing(2)

        self._key_letter_label = QLabel(display_letter)
        self._key_letter_label.setFont(QFont("monospace", 14, QFont.Weight.Bold))
        self._key_letter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._key_letter_label.setStyleSheet("color: #111111; background-color: transparent;")

        self._action_text_label = QLabel(action_label)
        action_text_font = QFont()
        action_text_font.setPointSize(7)
        self._action_text_label.setFont(action_text_font)
        self._action_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._action_text_label.setWordWrap(True)
        self._action_text_label.setStyleSheet("color: #2a2a2a; background-color: transparent;")

        badge_inner_layout.addWidget(self._key_letter_label)
        badge_inner_layout.addWidget(self._action_text_label)

        cell_layout = QVBoxLayout(self)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.addWidget(self._badge_frame)

        self._apply_color(_badge_color_for(canonical_letter))

    def _apply_color(self, color):
        self._badge_frame.setStyleSheet(
            f"QFrame {{ background-color: {_rgb_string(color)}; border-radius: 6px; }}"
        )

    def set_enabled_visual(self, enabled):
        """Visually grey the cell when *enabled* is False; restore otherwise."""
        self._enabled = enabled
        if enabled:
            self._apply_color(_badge_color_for(self._canonical_letter))
            self._key_letter_label.setStyleSheet("color: #111111; background-color: transparent;")
            self._action_text_label.setStyleSheet("color: #2a2a2a; background-color: transparent;")
        else:
            self._apply_color(_DISABLED_COLOR)
            self._key_letter_label.setStyleSheet("color: #aaaaaa; background-color: transparent;")
            self._action_text_label.setStyleSheet("color: #888888; background-color: transparent;")

    def mousePressEvent(self, event):  # noqa: N802 — Qt naming
        if not self._enabled:
            return
        import leader
        leader.dispatch_key(self._canonical_letter)


# ---------------------------------------------------------------------------
# Overlay dialog — Popup-flagged, frameless, non-activating.
# ---------------------------------------------------------------------------

class LeaderKeyOverlay(QDialog):
    """Floating HUD; show()/hide() driven by leader.arm()/_disarm()."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._cells_by_letter = {}
        self._build_ui()
        self.adjustSize()
        _apply_linux_hints(self)

    def _build_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 12, 16, 16)
        main_layout.setSpacing(10)

        title_label = QLabel("ANCHORS LEADER")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #cccccc;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # leader.physical_letter_for() honours the user's keyboard layout (AZERTY,
        # QWERTZ, …), so cells display the letter that's actually printed on the
        # user's physical key while still dispatching by canonical (QWERTY) name.
        import leader

        key_grid = QGridLayout()
        key_grid.setSpacing(8)

        for canonical_letter, action_label, row, col, _kind in LEADER_BINDINGS:
            display_letter = leader.physical_letter_for(canonical_letter)
            cell = ClickableKeyCell(canonical_letter, display_letter, action_label)
            self._cells_by_letter[canonical_letter] = cell
            key_grid.addWidget(cell, row, col)

        content_layout.addLayout(key_grid)

        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(4)

        sidebar_title = QLabel("KEYS")
        sidebar_title_font = QFont()
        sidebar_title_font.setBold(True)
        sidebar_title_font.setPointSize(8)
        sidebar_title.setFont(sidebar_title_font)
        sidebar_title.setStyleSheet("color: #888888;")
        sidebar_layout.addWidget(sidebar_title)

        for canonical_letter, action_label, _row, _col, _kind in LEADER_BINDINGS:
            display_letter = leader.physical_letter_for(canonical_letter)
            color = _badge_color_for(canonical_letter)
            sidebar_row_label = QLabel(
                f'<span style="color: {_rgb_string(color)}; font-weight: bold;">[{display_letter}]</span>'
                f'<span style="color: #aaaaaa;"> {action_label}</span>'
            )
            sidebar_row_label.setTextFormat(Qt.TextFormat.RichText)
            sidebar_row_font = QFont()
            sidebar_row_font.setPointSize(8)
            sidebar_row_label.setFont(sidebar_row_font)
            sidebar_layout.addWidget(sidebar_row_label)

        sidebar_layout.addStretch()
        content_layout.addWidget(sidebar_widget)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

    # -----------------------------------------------------------------------
    # Per-binding enable/disable based on selection + plugin state
    # -----------------------------------------------------------------------

    def refresh_for_selection(self):
        """Update each cell's enabled state based on the current selection.

        Delegates to leader._is_binding_enabled so the overlay grey-out and the
        actual dispatch gating share one source of truth.
        """
        import leader
        for letter, cell in self._cells_by_letter.items():
            cell.set_enabled_visual(leader._is_binding_enabled(letter))

    # -----------------------------------------------------------------------
    # Window plumbing
    # -----------------------------------------------------------------------

    def paintEvent(self, event):  # noqa: N802 — Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(20, 20, 20, 180))
        painter.setPen(QColor(180, 180, 180, 100))
        painter.drawRoundedRect(self.rect(), 8, 8)

    def show(self):
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        x = cursor_pos.x() - self.width() // 2
        y = cursor_pos.y() - self.height() // 2

        x = max(screen_geometry.left(), min(x, screen_geometry.right() - self.width()))
        y = max(screen_geometry.top(), min(y, screen_geometry.bottom() - self.height()))

        if sys.platform.startswith("linux"):
            self.setGeometry(x, y, self.width(), self.height())
        else:
            self.move(x, y)
        super().show()

    def hideEvent(self, event):  # noqa: N802 — Qt naming
        super().hideEvent(event)
        # Click-outside auto-closes a Popup-flagged dialog.  Route those hides
        # through _disarm() so leader state stays coherent.  Skip when the
        # leader module is hiding the overlay deliberately as part of a
        # chaining dispatch — that flag is set/unset around _overlay.hide() in
        # _hide_overlay_for_chaining().
        try:
            import leader
            if leader._suppress_disarm_on_hide:
                return
            leader._disarm()
        except Exception:
            pass

    def showEvent(self, event):  # noqa: N802 — Qt naming
        super().showEvent(event)
        if sys.platform == "win32":
            _apply_no_activate_win32(int(self.winId()))
            _restore_nuke_focus(self.parent())
