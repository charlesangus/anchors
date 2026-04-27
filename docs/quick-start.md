# Quick Start

An anchor is a named reference node that sits below an input in your DAG. A link points to it — drop one anywhere to re-pipe to the same source without copy-pasting the original. `Ctrl+C`/`Ctrl+V` are context-aware replacements for Nuke's built-in clipboard that handle hidden inputs automatically.

_Anchors_ differentiates between three "tiers" of anchors:

- Anchors - the most "official" anchor; created with "Create Anchor" or by pressing "A" with a node selected
  - semantically, these are intended for re-use throughout the script, e.g. the plate, the camera; the use of an Anchor implies "this is important"
- Dot anchors - Dots with labels ≥33pt font; created by selecting a Dot and using Shift-B, Shift-N, or Shift-M to apply a small/medium/large label.
  - these are "places in the comp"; e.g. it's best to put a large-label dot at the bottom of a module, medium at the bottom of a submodule, etc.
  - largely for script navigation, but also modules often need to refer to each other, and this is a handy way to do it
- Local anchors - hidden-input dots used just to clean up the layout
  - implies there's no larger picture to this connection, it's just for clarity/script layout
  - does not reconnect by name across scripts (unlike Link nodes pointing to Anchors and Dot Anchors, which when pasted into a new script will try to reconnect to the "same" anchor)

## Creating and Editing Anchors

1. Select any node and press `A` — the anchor creation dialog opens, pre-filled with a name derived from the node's file path and the smallest enclosing backdrop label.
2. Edit the name if needed. Optionally, choose a colour or create a custom colour. An anchor node appears below your selection, wired to it.

![Anchor naming dialog with name pre-filled from the input node](img/anchor-create-dialog.png)

**Nothing selected — creating a link instead:**

3. Press `A` with nothing selected — a fuzzy-search picker opens listing all anchors in the script. Select one and a link node is created and wired at the cursor position.

![Link creation picker showing available anchors](img/link-creation-picker.png)

**Anchor already selected — renaming:**

4. Select an existing anchor and press `A` — the rename dialog opens pre-filled with the current name. Edit and confirm. All link nodes pointing to that anchor update automatically.

![Rename dialog with current anchor name pre-filled](img/anchor-rename-dialog.png)

**Unanchored Dot selected — promoting to a Dot anchor:**

5. Select a plain Dot node and press "Shift-B", "Shift-N", or "Shift-M".
6. Enter a label. The Dot is promoted to a Dot anchor in place.

![Dot size picker for anchor promotion](img/dot-size-picker.png)

**Color picker:**

7. The color picker is available in the creation dialog and the rename dialog. Click the color swatch to open it and choose a color. The color is applied to the anchor and all its link nodes.
8. Hit "Tab" to display a shortcut over each swatch. Press the two keys of the shortcut sequentially to select that colour and close the dialog. E.g. to select the first option, press Tab-A-1 one at a time.

![Color picker in anchor dialog](img/anchor-color-picker.png)

## Navigating to Anchors

1. Press `Alt+A` — a fuzzy-search picker opens listing all anchors and labelled backdrops in the script with their colors.

![Anchor navigation picker](img/anchor-navigate-picker.png)

2. Select an anchor — the DAG zooms to its location.
3. Press `Alt+Z` to return to the previous DAG position.

**Other navigation shortcuts:**

- `Alt+J` — with a Link node selected, jump straight to its source anchor.
- `Alt+L` — with an anchor selected, cycle through each Link node that references it. Press again to advance to the next Link; after the last Link, returns to the anchor.

## Copy and Paste

1. Select nodes and press `Ctrl+C` — input nodes (Read, Camera, etc.) are automatically converted to hidden-input proxies in the clipboard.
2. Press `Ctrl+V` to paste — proxies are re-piped to their original input nodes if those nodes exist in the same script at the same level.
3. To paste without the Link nodes (raw paste), use Ctrl-Shift-D.
4. This setting can be disabled in the "Anchor Preferences..." in Edit>Anchors.

![Before and after paste showing hidden-input reconnection](img/copy-paste-reconnection.png)

## Keyboard Reference

| Shortcut | Action |
|----------|--------|
| `A` | Create anchor (node selected), open link picker (nothing selected), or rename anchor (anchor selected) |
| `Alt+A` | Open anchor navigation picker — jump DAG to any anchor or labelled backdrop |
| `Alt+J` | Jump to source anchor (Link selected) |
| `Alt+L` | Cycle through Link nodes pointing at the selected anchor |
| `Alt+Z` | Return to previous DAG position |
| `Ctrl+C` | Copy with hidden-input conversion |
| `Ctrl+V` | Paste with smart hidden-input reconnection |
| `Ctrl+Shift+D` | Paste (old-style — no re-piping) |
| `Shift+B` | Small Dot label (promotes plain Dot to a Dot anchor) |
| `Shift+N` | Medium Dot label (promotes plain Dot to a Dot anchor) |
| `Shift+M` | Large Dot label (promotes plain Dot to a Dot anchor) |
| `Ctrl+M` | Append text to the selected node's label |

