"""Leader-key event filter and state machine for the anchors plugin.

``arm()`` is the sole public entry point.  It is bound to Shift+A in menu.py
with shortcutContext=2 (DAG-only focus) so this module never has to do its
own focus check.

Lifecycle
---------
1. The user presses Shift+A.
2. ``arm()`` flips ``_leader_active`` to True, installs a single ``LeaderKeyFilter``
   on QApplication, and schedules the overlay to appear after a brief delay.
3. The next QKeyEvent is intercepted by the filter:
     - A *single-shot* binding (Q, W, E, R, F, J, Z, X, comma) disarms first,
       then dispatches.
     - A *chaining* binding (L) hides the overlay, dispatches, and stays armed
       for further chaining keys.
     - Anything else (or a mouse click) disarms cleanly.

The Win32 / Linux taskbar suppression code lives in leader_overlay.py — see
the docstrings there for why those work-arounds were necessary.
"""

import contextlib

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Module-level singletons / state
# ---------------------------------------------------------------------------

_leader_active = False
_filter = None
_overlay = None
_overlay_timer = None

# Set True around any programmatic _overlay.hide() call that should NOT disarm
# leader mode (i.e. chaining hides).  hideEvent on the overlay reads this and
# skips its _disarm() call when set.  Keeps click-outside disarms working
# (those flow through hideEvent without this flag set).
_suppress_disarm_on_hide = False

# Delay before the overlay appears.  Short enough that touch-typists never
# see it; long enough that fast Shift+A → key sequences never flash it.
_OVERLAY_DELAY_MS = 200


# ---------------------------------------------------------------------------
# Dispatch helpers — inline imports keep startup cheap and avoid cycles.
# ---------------------------------------------------------------------------

def _dispatch_set_input_to_b():
    import input_sets
    input_sets.set_input_to_b()


def _dispatch_set_input_to_a():
    import input_sets
    input_sets.set_input_to_a()


def _dispatch_set_input_to_mask():
    import input_sets
    input_sets.set_input_to_mask()


def _dispatch_set_input_first_available():
    import input_sets
    input_sets.set_input_to_first_available()


def _dispatch_anchor_find():
    import anchor
    anchor.select_anchor_and_navigate()


def _dispatch_anchor_jump():
    import anchor
    anchor.jump_to_selected_anchor()


def _dispatch_cycle_links():
    import anchor
    anchor.cycle_next_link()


def _dispatch_anchor_back():
    import anchor
    anchor.navigate_back()


def _dispatch_reconnect_all_links():
    import anchor
    anchor.reconnect_all_links()


def _dispatch_open_prefs():
    from colors import PrefsDialog
    PrefsDialog().exec()


# ---------------------------------------------------------------------------
# Keyboard-layout remap.
#
# We bind by *physical key position*, not by produced letter.  Without a remap,
# pressing the top-left letter on an AZERTY keyboard (which types 'A') would
# fail to trigger the Q binding.  We detect the user's layout via QLocale and
# rewrite Qt.Key codes accordingly so the user's muscle memory works regardless
# of layout.
#
# The mapping is QWERTY-canonical-letter → letter-physically-at-that-position.
# Example: on AZERTY the top-left letter key is 'A', so Q → A.
# ---------------------------------------------------------------------------

def _build_layout_remap():
    """Return a dict mapping QWERTY canonical letters to current-layout letters.

    Heuristic based on system locale.  Returns {} (identity / QWERTY) for
    unknown layouts or when QLocale is unavailable / mocked in tests.
    """
    try:
        from PySide6.QtCore import QLocale
        locale_name = QLocale.system().name()
        if not isinstance(locale_name, str):
            return {}
        lang, _, country = locale_name.partition("_")
        # AZERTY: France, Belgium
        if country in ("FR", "BE") or lang == "fr":
            return {"Q": "A", "W": "Z", "A": "Q", "Z": "W"}
        # QWERTZ: Germany, Austria, Switzerland, Czech, Slovak, Slovenian, Croatian
        if country in ("DE", "AT", "CH") or lang in ("de", "cs", "sk", "sl", "hr"):
            return {"Y": "Z", "Z": "Y"}
    except Exception:
        pass
    return {}


LAYOUT_REMAP = _build_layout_remap()


def _letter_to_qt_key(letter):
    if letter == ',':
        return Qt.Key.Key_Comma
    return getattr(Qt.Key, f'Key_{letter}', None)


def physical_letter_for(canonical_letter):
    """Return the letter the user physically types to invoke the *canonical_letter* binding.

    Public so leader_overlay.py can render the right glyph on each cell.
    Comma and any unmapped letter pass through unchanged.
    """
    return LAYOUT_REMAP.get(canonical_letter, canonical_letter)


# ---------------------------------------------------------------------------
# Dispatch tables — split into single-shot and chaining.
# Keyed by Qt.Key codes that the OS will actually deliver on the user's
# layout (i.e. post-remap).
# ---------------------------------------------------------------------------

_DISPATCH_PAIRS = (
    ('Q', _dispatch_set_input_to_b),
    ('W', _dispatch_set_input_to_a),
    ('E', _dispatch_set_input_to_mask),
    ('R', _dispatch_set_input_first_available),
    ('F', _dispatch_anchor_find),
    ('J', _dispatch_anchor_jump),
    ('Z', _dispatch_anchor_back),
    ('X', _dispatch_reconnect_all_links),
    (',', _dispatch_open_prefs),
)

_CHAINING_PAIRS = (
    ('L', _dispatch_cycle_links),
)


def _build_dispatch_tables():
    """Return (single, chaining, qt_to_letter) — all three Qt.Key-keyed."""
    single = {}
    chaining = {}
    qt_to_letter = {}
    for canonical_letter, fn in _DISPATCH_PAIRS:
        physical = physical_letter_for(canonical_letter)
        qt_key = _letter_to_qt_key(physical)
        if qt_key is not None:
            single[qt_key] = fn
            qt_to_letter[qt_key] = canonical_letter
    for canonical_letter, fn in _CHAINING_PAIRS:
        physical = physical_letter_for(canonical_letter)
        qt_key = _letter_to_qt_key(physical)
        if qt_key is not None:
            chaining[qt_key] = fn
            qt_to_letter[qt_key] = canonical_letter
    return single, chaining, qt_to_letter


_DISPATCH_TABLE, _CHAINING_DISPATCH_TABLE, _QT_KEY_TO_LETTER = _build_dispatch_tables()


# ---------------------------------------------------------------------------
# Per-binding enable check.
# Used by both the event filter / dispatch_key (to ignore presses on greyed
# bindings) and leader_overlay.refresh_for_selection (to grey them visually).
# ---------------------------------------------------------------------------


def _selected_non_link_target():
    """Return the currently-selected single non-link node, or None.

    Mirrors input_sets._selected_target_node so the enable predicates in
    input_sets receive exactly the same target the dispatchers will see.
    """
    try:
        import nuke
        from link import is_link
        selected = nuke.selectedNodes()
        if len(selected) != 1:
            return None
        if is_link(selected[0]):
            return None
        return selected[0]
    except Exception:
        return None


def _selected_single_node():
    """Return the only selected node (of any kind), or None."""
    try:
        import nuke
        selected = nuke.selectedNodes()
        if len(selected) == 1:
            return selected[0]
    except Exception:
        pass
    return None


def _is_binding_enabled(letter):
    """Return True if pressing *letter* should fire its dispatcher right now.

    Single source of truth for both:
      - dispatch gating (event filter and dispatch_key use this to silently
        disarm when the user presses a greyed key — no surprise wiring)
      - the overlay's grey-out (refresh_for_selection consults this)

    Comma (Preferences) is always enabled, even when the plugin is disabled,
    so the user can re-enable from the dialog.  All other anchor commands
    require prefs.plugin_enabled.
    """
    if letter == ',':
        return True

    import prefs
    if not prefs.plugin_enabled:
        return False

    if letter in ('Q', 'W', 'E', 'R'):
        import input_sets
        target_node = _selected_non_link_target()
        if letter == 'Q':
            return input_sets.can_set_input_b(target_node)
        if letter == 'W':
            return input_sets.can_set_input_a(target_node)
        if letter == 'E':
            return input_sets.can_set_input_mask(target_node)
        if letter == 'R':
            return input_sets.can_set_input_first_available(target_node)

    if letter == 'J':
        # Anchor Jump goes from a Link node up to its source anchor.
        from link import is_link
        node = _selected_single_node()
        return node is not None and is_link(node)

    if letter == 'L':
        # Cycle Links steps through links of the selected anchor.
        from link import is_anchor
        node = _selected_single_node()
        return node is not None and is_anchor(node)

    if letter == 'Z':
        # Navigate-back is only meaningful when a back position has been saved.
        import anchor
        return anchor._back_position is not None

    # F / X — always available when the plugin is enabled.
    return True


# ---------------------------------------------------------------------------
# LeaderKeyFilter — Qt event filter installed on QApplication during leader mode.
# ---------------------------------------------------------------------------

class LeaderKeyFilter(QObject):
    """Intercepts key/mouse events while leader mode is armed.

    ShortcutOverride is consumed first — otherwise Nuke's own shortcut system
    matches single keys (e.g. ``F`` → fullscreen) before our KeyPress handler
    runs.  This is the load-bearing trick that makes the leader work at all.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Named timer instance so _disarm() can stop it.  QTimer.singleShot()
        # returns None and cannot be cancelled.
        self._overlay_timer = QTimer()
        self._overlay_timer.setSingleShot(True)
        global _overlay_timer
        _overlay_timer = self._overlay_timer

    def eventFilter(self, watched, event):  # noqa: N802 — Qt naming
        global _leader_active
        if not _leader_active:
            return False

        event_type = event.type()

        if event_type == QEvent.Type.ShortcutOverride:
            event.accept()
            return True

        if event_type == QEvent.Type.KeyPress:
            if event.isAutoRepeat():
                return True

            key = event.key()

            # Recognise the key against the bindings table; gate on enable
            # state so a greyed binding (e.g. W on a single-input node) silently
            # disarms instead of firing the wrong wiring.
            letter = _QT_KEY_TO_LETTER.get(key)
            if letter is None or not _is_binding_enabled(letter):
                _disarm()
                return True

            chaining_function = _CHAINING_DISPATCH_TABLE.get(key)
            if chaining_function is not None:
                _hide_overlay_for_chaining()
                chaining_function()
                return True

            dispatch_function = _DISPATCH_TABLE.get(key)
            if dispatch_function is not None:
                _disarm()
                dispatch_function()
                return True

            # Recognised but with no dispatcher — should not happen given the
            # _QT_KEY_TO_LETTER → enable-check gate above.
            _disarm()
            return True

        if event_type == QEvent.Type.MouseButtonPress:
            # Click during leader mode: disarm but let the click propagate so
            # the user's intended click still fires.
            _disarm()
            return False

        return False


# ---------------------------------------------------------------------------
# Public entry point + internal helpers
# ---------------------------------------------------------------------------

def arm():
    """Activate leader-key mode.

    Idempotent — re-arming while already armed is a no-op.  Lazily creates
    the filter and overlay singletons on first call.
    """
    global _leader_active, _filter, _overlay

    if _leader_active:
        return

    if _filter is None:
        _filter = LeaderKeyFilter()

    # Lazy-import the overlay so importing leader.py doesn't drag in the full
    # Qt widget hierarchy at Nuke startup (when init.py runs menu.py).
    if _overlay is None:
        try:
            from leader_overlay import LeaderKeyOverlay
            _overlay = LeaderKeyOverlay()
        except Exception:
            # Overlay creation must never block leader mode itself.
            _overlay = None

    _leader_active = True
    QApplication.instance().installEventFilter(_filter)

    if _overlay is not None and _overlay_timer is not None:
        with contextlib.suppress(RuntimeError):
            _overlay_timer.timeout.disconnect()
        _overlay_timer.timeout.connect(_show_overlay)
        _overlay_timer.start(_OVERLAY_DELAY_MS)


def _show_overlay():
    """Refresh the overlay's per-key enable/disable state and show it."""
    if _overlay is None:
        return
    try:
        _overlay.refresh_for_selection()
    except AttributeError:
        pass
    _overlay.show()


def _disarm():
    """Deactivate leader-key mode and tear everything down.

    Safe to call from inside eventFilter — Qt explicitly allows
    removeEventFilter during event delivery.
    """
    global _leader_active
    if not _leader_active:
        return
    _leader_active = False
    app = QApplication.instance()
    if app is not None and _filter is not None:
        app.removeEventFilter(_filter)
    if _overlay_timer is not None:
        _overlay_timer.stop()
    if _overlay is not None:
        _overlay.hide()


def _hide_overlay_for_chaining():
    """Hide the overlay during a chaining dispatch without disarming.

    Sets _suppress_disarm_on_hide so the overlay's hideEvent skips its
    _disarm() call (the click-outside auto-close path still disarms because
    that path doesn't go through here).  Also stops the show timer so a
    pending overlay show after this hide doesn't pop the overlay back up
    while the user is still chaining.
    """
    global _suppress_disarm_on_hide
    if _overlay_timer is not None:
        _overlay_timer.stop()
    if _overlay is None:
        return
    _suppress_disarm_on_hide = True
    try:
        _overlay.hide()
    finally:
        _suppress_disarm_on_hide = False


def dispatch_key(canonical_letter):
    """Dispatch as if the user pressed the binding for *canonical_letter*.

    Used by overlay click cells, which always pass the canonical (QWERTY) letter
    so the same dispatcher runs regardless of layout.  Mirrors the eventFilter
    routing — single-shot keys disarm first, chaining keys hide the overlay
    and stay armed.
    """
    canonical_letter = canonical_letter if canonical_letter == ',' else canonical_letter.upper()
    physical_letter = physical_letter_for(canonical_letter)
    qt_key = _letter_to_qt_key(physical_letter)
    if qt_key is None:
        return

    # Same enable gate as the keyboard path.  Greyed cells are still clickable
    # because Qt routes mousePressEvent through here regardless; refuse to
    # dispatch when the binding is disabled.
    if not _is_binding_enabled(canonical_letter):
        _disarm()
        return

    chaining_function = _CHAINING_DISPATCH_TABLE.get(qt_key)
    if chaining_function is not None:
        _hide_overlay_for_chaining()
        chaining_function()
        return

    dispatch_function = _DISPATCH_TABLE.get(qt_key)
    if dispatch_function is not None:
        _disarm()
        dispatch_function()
