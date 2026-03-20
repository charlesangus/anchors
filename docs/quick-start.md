# Quick Start

An anchor is a named reference node that sits below an input in your DAG. A link points to it — drop one anywhere to re-pipe to the same source without copy-pasting the original. `Ctrl+C`/`Ctrl+V` are context-aware replacements for Nuke's built-in clipboard that handle hidden inputs automatically.

## Creating Anchors

1. Select any node and press `A` — the anchor creation dialog opens, pre-filled with a name derived from the node's file path and the smallest enclosing backdrop label.
2. Edit the name if needed, pick a color in the dialog, and press OK. An anchor node appears below your selection, wired to it.

![Anchor naming dialog with name pre-filled from the input node](img/anchor-create-dialog.png)

**Nothing selected — creating a link instead:**

3. Press `A` with nothing selected — a fuzzy-search picker opens listing all anchors in the script. Select one and a link node is created and wired at the cursor position.

![Link creation picker showing available anchors](img/link-creation-picker.png)

**Anchor already selected — renaming:**

4. Select an existing anchor and press `A` — the rename dialog opens pre-filled with the current name. Edit and confirm. All link nodes pointing to that anchor update automatically.

![Rename dialog with current anchor name pre-filled](img/anchor-rename-dialog.png)

**Unanchored Dot selected — promoting to a Dot anchor:**

5. Select a plain Dot node and press `A` — a size picker appears first (Medium / Large label).
6. Choose a size, then enter a label. The Dot is promoted to a Dot anchor in place.

![Dot size picker for anchor promotion](img/dot-size-picker.png)

**Color picker:**

7. The color picker is available in the creation dialog and the rename dialog. Click the color swatch to open it and choose a color. The color is applied to the anchor and all its link nodes.

![Color picker in anchor dialog](img/anchor-color-picker.png)

## Navigating to Anchors

1. Press `Alt+A` — a fuzzy-search picker opens listing all anchors in the script with their colors.

![Anchor navigation picker](img/anchor-navigate-picker.png)

2. Select an anchor — the DAG zooms to its location.
3. Press `Alt+Z` to return to the previous DAG position.

## Copy and Paste

1. Select nodes and press `Ctrl+C` — input nodes (Read, Camera, etc.) are automatically converted to hidden-input proxies in the clipboard.
2. Press `Ctrl+V` to paste — proxies are re-piped to their original input nodes if those nodes exist in the same script at the same level.

![Before and after paste showing hidden-input reconnection](img/copy-paste-reconnection.png)

3. This behavior can be disabled via Preferences.

See `README.md` for edge cases: cross-script paste, old-style paste, and LINK_CLASSES passthrough mode.

## Keyboard Reference

| Shortcut | Action |
|----------|--------|
| `A` | Create anchor (node selected), open link picker (nothing selected), rename anchor (anchor selected), or promote Dot to anchor (Dot selected) |
| `Alt+A` | Open anchor navigation picker — jump DAG to any anchor |
| `Alt+Z` | Return to previous DAG position |
| `Ctrl+C` | Copy with hidden-input conversion |
| `Ctrl+V` | Paste with smart hidden-input reconnection |

See `README.md` for the full shortcut list.
