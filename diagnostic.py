"""Temporary diagnostic module — DO NOT SHIP.

Tests Group context behaviour across four open questions.
Wire into menu.py with:

    import diagnostic
    diagnostic.register_menu()

Then remove once questions are answered.
"""

import nuke
import tabtabtab as _tabtabtab

try:
    from PySide6.QtCore import Qt
    from PySide6 import QtWidgets
except ImportError:
    from PySide2.QtCore import Qt
    from PySide2 import QtWidgets


# ---------------------------------------------------------------------------
# Test 1 + 4: nuke.exists() in Qt signal context AND nuke.zoomToFitSelected()
#
# Open this picker from inside a Group (navigated) and select an anchor that
# belongs to that Group. The output will show:
#   - Whether nuke.exists(node.name()) works in the Qt signal
#   - Whether nuke.exists(node.fullName()) works in the Qt signal
#   - What nuke.thisGroup() and nuke.lastHitGroup() are inside the Qt signal
#   - Whether nuke.zoomToFitSelected() zooms the Group's DAG or root DAG
# ---------------------------------------------------------------------------

class _DiagnosticNavigatePlugin(_tabtabtab.TabTabTabPlugin):
    """Lists all nodes from nuke.allNodes() and prints diagnostic info on selection."""

    def get_items(self):
        # Called in menu-callback context — report what allNodes() returns here
        all_nodes = nuke.allNodes()
        print(f"\n[DIAG get_items] nuke.thisGroup()      = {nuke.thisGroup()!r}")
        print(f"[DIAG get_items] nuke.lastHitGroup()   = {nuke.lastHitGroup()!r}")
        print(f"[DIAG get_items] nuke.allNodes() count = {len(all_nodes)}")
        print(f"[DIAG get_items] nuke.allNodes() names = {[n.name() for n in all_nodes]}")
        return [
            {'menuobj': n, 'menupath': f'Nodes/{n.name()} ({n.Class()})'}
            for n in all_nodes
        ]

    def get_weights_file(self):
        return '/tmp/diag_weights.json'

    def invoke(self, thing):
        # Called in Qt signal context — this is the key test
        node = thing['menuobj']
        local_name = node.name()
        full_name = node.fullName()
        exists_local = nuke.exists(local_name)
        exists_full  = nuke.exists(full_name)

        print(f"\n[DIAG invoke] === Qt signal context ===")
        print(f"[DIAG invoke] node.name()                 = {local_name!r}")
        print(f"[DIAG invoke] node.fullName()              = {full_name!r}")
        print(f"[DIAG invoke] nuke.exists(node.name())     = {exists_local}")
        print(f"[DIAG invoke] nuke.exists(node.fullName()) = {exists_full}")
        print(f"[DIAG invoke] nuke.thisGroup()             = {nuke.thisGroup()!r}")
        print(f"[DIAG invoke] nuke.lastHitGroup()          = {nuke.lastHitGroup()!r}")

        # Test 4: does nuke.zoomToFitSelected() zoom the right panel?
        # We'll select the node and zoom — look at which DAG panel scrolls.
        import nukescripts
        nukescripts.clear_selection_recursive()
        try:
            node['selected'].setValue(True)
            print(f"[DIAG invoke] Calling nuke.zoomToFitSelected() — watch which panel scrolls...")
            nuke.zoomToFitSelected()
            print(f"[DIAG invoke] nuke.zoomToFitSelected() returned — did the correct DAG zoom?")
        except Exception as exc:
            print(f"[DIAG invoke] nuke.zoomToFitSelected() raised: {exc!r}")
        nukescripts.clear_selection_recursive()


_diag_navigate_widget = None


def open_diagnostic_navigate():
    """Test 1 + 4: Open from inside a Group (navigated) to test Qt signal context."""
    global _diag_navigate_widget
    _diag_navigate_widget = _tabtabtab.TabTabTabWidget(
        _DiagnosticNavigatePlugin(), winflags=Qt.FramelessWindowHint
    )
    _diag_navigate_widget.under_cursor()
    _diag_navigate_widget.show()
    _diag_navigate_widget.raise_()


# ---------------------------------------------------------------------------
# Test 2: What does the menu-callback context look like in Group View?
#
# Group View = Group internals opened as a floating panel at root level.
# Invoke this from that floating panel and check the output.
# Also invoke from inside a navigated Group and from root for comparison.
# ---------------------------------------------------------------------------

def report_context():
    """Test 2: Print context info. Run from root, inside Group, and Group View."""
    all_nodes = nuke.allNodes()
    print(f"\n[DIAG context] === Menu callback context ===")
    print(f"[DIAG context] nuke.thisGroup()             = {nuke.thisGroup()!r}")
    print(f"[DIAG context] nuke.lastHitGroup()          = {nuke.lastHitGroup()!r}")
    print(f"[DIAG context] nuke.allNodes() count        = {len(all_nodes)}")
    print(f"[DIAG context] nuke.allNodes() names        = {[n.name() for n in all_nodes]}")
    print(f"[DIAG context] nuke.root()                  = {nuke.root()!r}")


# ---------------------------------------------------------------------------
# Test 3: Copy/paste context in Group View
#
# Press Ctrl+C from the Group View floating panel — this replaces the real
# copy_anchors() and prints what context it sees before delegating.
# ---------------------------------------------------------------------------

def diagnostic_copy():
    """Test 3: Print context seen by copy callback. Bind to Ctrl+C to replace real copy."""
    all_nodes = nuke.allNodes()
    selected   = nuke.selectedNodes()
    print(f"\n[DIAG copy] === Copy callback context ===")
    print(f"[DIAG copy] nuke.thisGroup()             = {nuke.thisGroup()!r}")
    print(f"[DIAG copy] nuke.lastHitGroup()          = {nuke.lastHitGroup()!r}")
    print(f"[DIAG copy] nuke.allNodes() count        = {len(all_nodes)}")
    print(f"[DIAG copy] nuke.allNodes() names        = {[n.name() for n in all_nodes]}")
    print(f"[DIAG copy] nuke.selectedNodes() count   = {len(selected)}")
    print(f"[DIAG copy] nuke.selectedNodes() names   = {[n.name() for n in selected]}")
    # Delegate to real copy so the operation still works
    import anchors
    anchors.copy_anchors()


def register_menu():
    """Add diagnostic commands to a temporary Diagnostic menu."""
    menu = nuke.menu("Nuke")
    diag = menu.addMenu("Diagnostic")

    # Test 1 + 4: open the navigate picker — invoke from inside a Group
    diag.addCommand(
        "Test 1+4: Navigate picker (inside Group)",
        "diagnostic.open_diagnostic_navigate()",
        "alt+D",
    )

    # Test 2: context report — invoke from root, then Group View, then inside Group
    diag.addCommand(
        "Test 2: Report context",
        "diagnostic.report_context()",
        "shift+D",
    )

    # Test 3: diagnostic copy — invoke from Group View with nodes selected
    # Note: this *replaces* Ctrl+C temporarily; remove after testing
    diag.addCommand(
        "Test 3: Diagnostic copy (Group View)",
        "diagnostic.diagnostic_copy()",
    )
