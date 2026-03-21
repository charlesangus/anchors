# Anchors

Replacement and improvement for the Copy/Cut/Paste functions in Foundry's Nuke, with a full anchor-and-link system for reusable named inputs.

# Installation

Copy the `anchors` folder into your `~/.nuke` folder and add this line to your top-level `init.py`:

`nuke.pluginAddPath('anchors')`

The included `menu.py` will handle replacing the built-in copy/paste functions.

# Why

I am a firm believer that it is impossible to have an organized script without hidden inputs for any but the most trivial scripts. However, working with hidden inputs is painful. Unlike a Read node, which stays pointing at the same file sequence when you copy-paste it, a hidden input must be re-piped every time it's pasted. This is pointless busy-work, as the cases where we do and do not want a hidden input re-piped are well-defined and consistent:

```If the parent node is not in the selection, AND the parent node is at the "same level" as the pasted node (i.e. at the Root level or in the same Group node) AND in the same script, AND the node in question is a valid class to have hidden inputs (i.e. PostageStamp/NoOp/Dot), re-pipe.```

If the parent node is in the selection, the parent and child will be pasted together with their inputs intact, so we don't need to re-pipe. Nuke handles this automatically, as it does all inputs where both nodes are pasted together.

If the parent node is not at the same level, re-piping cannot occur. Nuke (unlike e.g. Houdini) cannot connect nodes that do not exist at the same level.

If the parent node is not in the same script, re-piping cannot occur. Nuke cannot connect nodes across scripts (LiveGroups aside).

I am a firm believer that the ONLY nodes that should ever have hidden inputs are PostageStamps/NoOps/Dots. These nodes have exactly one input, and serve as "placeholders" for the input that has been hidden, providing a visual reference of the connection's existence. Without this visual reference of the hidden input, the script becomes immediately confusing.

# Quick-start

See docs/quick-start.md for an artist-friendly introduction to the basic functionality.

# How

There are no callbacks. Everything is handled by over-riding the builtin copy-paste functions. Hidden knobs are added to relevant nodes as copying is conducted, and the magic happens at paste time. If you re-pipe nodes yourself, labels etc. will not update as nothing is live.

The anchor system lives alongside copy/paste and provides a reusable named-input mechanism for the node graph. Anchors and their links are plain Nuke nodes; the system is stateless and survives script save/load without callbacks.

# Copy / Paste

`Ctrl+C`, `Ctrl+X`, and `Ctrl+V` are replaced with hidden-aware versions:

- **Input nodes** (Read, Camera, ReadGeo, DeepRead, etc.) are converted to hidden-input PostageStamp/NoOp proxies on copy. When pasted, the proxy is re-piped to the original input node automatically, provided the original is in the same script and at the same level.
- **Paste Multiple** (`Edit > Paste Multiple`) pastes the clipboard contents multiple times in sequence, with full hidden-input re-piping applied each time.
- **Old-style paste** (no re-piping magic): `Edit > Anchors > Paste (old)` / `Ctrl+Shift+D`. Old-style copy and cut are also available under `Edit > Anchors`.

# Anchor System

The anchor system is a reusable named-input mechanism for the node graph.

## Concepts

- **Anchor** — a named NoOp (node name prefixed `Anchor_`) or labeled Dot node that sits below an input node and acts as a stable reference point. Each anchor has a "Reconnect Child Links" button and a "Rename" button in its properties panel.
- **Link** — a PostageStamp, NoOp, or Dot node that references an anchor by fully-qualified name. Automatically re-pipes itself when reconnected. Displays a `Link: <name>` label.

## Creating Anchors

- Select a node and press `A` (or `Edit > Anchors > Create Anchor`) — a name dialog appears, pre-filled from the input node's file path and the smallest containing backdrop label.
- **Dot anchors**: select a Dot node and press `A` to promote it to a Dot anchor. A size picker (Medium / Large label) appears first, then a label prompt.
- **Rename**: if an anchor is already selected when you press `A`, the rename dialog opens instead of creating a new anchor.

## Creating Links

- With no node selected, press `A` (or `Edit > Anchors > Create Link`) — a fuzzy-search picker appears listing all anchors with their colors. Pick one and a link node is created and wired.

## Renaming

- Select an anchor and press `A` — the rename dialog opens, pre-filled with the current name (NoOp anchors) or label (Dot anchors).
- Or: `Edit > Anchors > Rename Anchor`.
- All link nodes referencing the anchor are updated automatically.

## Navigating

- `Alt+A` (or `Edit > Anchors > Anchor Find`) — opens a fuzzy-search picker to jump the DAG view to any anchor.

## Reconnecting

- `Edit > Anchors > Reconnect All Links` — re-wires all link nodes in the script. Useful after a script load or merge.
- The "Reconnect Child Links" button on each anchor node re-wires only that anchor's links.

## Colors

Anchors inherit their tile color using this priority:

1. The smallest containing BackdropNode — only when the anchor's input is a Read node.
2. The input node's tile color (with Preferences fallback).
3. Default purple (`#6f3399`) if neither is available.

Link nodes inherit the same color as their anchor.

## Auto-Naming

The suggested anchor name is derived from the input node's file knob: the basename is taken, any trailing `_v<number>` version suffix and file extension are stripped, and the result is prefixed with the smallest containing backdrop's label (if any).

# Label Utilities

Keyboard shortcuts for quickly labeling Dot anchors and other nodes (available under `Edit > Anchors`):

| Shortcut | Action |
|---|---|
| `Shift+M` | Label (Large) — prompts for a label; applies large font to Dots and other nodes |
| `Shift+N` | Label (Medium) — prompts for a label; applies medium font to Dots, unchanged for other nodes |
| `Ctrl+M` | Append Label — prompts for a suffix and appends it to the existing label |

For Dot anchors, applying or appending a label also propagates the change to all link nodes pointing at that Dot.

# Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+C` | Copy (hidden) |
| `Ctrl+X` | Cut (hidden) |
| `Ctrl+V` | Paste (hidden) |
| `Ctrl+Shift+D` | Paste (old-style, no re-piping) |
| `A` | Anchor shortcut (context-sensitive: create anchor, promote Dot, rename, or open link picker) |
| `Alt+A` | Anchor Find (navigate DAG to an anchor) |
| `Shift+M` | Label (Large) |
| `Shift+N` | Label (Medium) |
| `Ctrl+M` | Append Label |

# Configuration

Edit `constants.py` to change the default behaviour:

- **`HIDDEN_INPUT_CLASSES`** — list of node classes that are treated as hidden-input proxies (default: `PostageStamp`, `Dot`, `NoOp`).
- **`LINK_CLASSES`** — dict mapping source node classes to the proxy class used when creating links or copying (e.g. `Read → PostageStamp`, `Camera → NoOp`).

# Python API

The following functions are stable entry points for tools and scripts that want to integrate with anchors programmatically.

## Anchors (`import anchor`)

### Querying

```python
anchor.all_anchors() -> list[nuke.Node]
```
Returns all anchor nodes in the current script, sorted alphabetically by display name.

```python
anchor.find_anchor_by_name(display_name: str) -> nuke.Node | None
```
Looks up an anchor by its display name (the label shown in the node graph). Returns `None` if not found.

```python
anchor.get_links_for_anchor(anchor_node: nuke.Node) -> list[nuke.Node]
```
Returns all link nodes in the current script that reference the given anchor node. Useful for impact analysis before renaming or deleting an anchor.

---

### Creating anchors

```python
anchor.create_anchor_named(name: str, input_node: nuke.Node | None = None) -> nuke.Node
```
Creates an anchor with the given name. Positions it below `input_node` and wires it up if provided. Returns the new anchor node.
Raises `ValueError` if `name` sanitizes to an empty string (i.e. contains no alphanumeric characters or underscores).

```python
anchor.create_anchor_silent(input_node: nuke.Node | None = None) -> nuke.Node
```
Creates an anchor using the auto-suggested name derived from the input node's file path and surrounding backdrop. Falls back to the node's name, then to `"Anchor"` if no suggestion can be derived. Returns the new anchor node.

```python
anchor.create_anchor()
```
Prompts the user for a name (pre-filled with the auto-suggestion) and creates the anchor. Intended for interactive use via keybind or menu.

---

### Creating links

```python
anchor.create_from_anchor(anchor_node: nuke.Node) -> nuke.Node
```
Creates a link node wired to the given anchor node and returns it. The link node class (PostageStamp, NoOp, Dot) is chosen based on the anchor's input.

```python
anchor.create_link_for_anchor_named(display_name: str) -> nuke.Node
```
Looks up the anchor by display name, creates a link node wired to it, and returns the link node.
Raises `ValueError` if no anchor with that display name exists.

```python
anchor.try_create_link_for_anchor_named(display_name: str) -> nuke.Node | None
```
Same as above but returns `None` instead of raising if the anchor is not found.

---

### Renaming

```python
anchor.rename_anchor_to(anchor_node: nuke.Node, name: str)
```
Renames the anchor to `name` and updates the stored reference and label on all link nodes that point to it.
Raises `ValueError` if `name` sanitizes to an empty string (NoOp anchors only; Dot anchors update the label directly).

```python
anchor.rename_anchor(anchor_node: nuke.Node)
```
Prompts the user for a new name (pre-filled with a suggestion) and renames the anchor. Intended for interactive use.

```python
anchor.rename_selected_anchor()
```
Renames the currently selected anchor. Does nothing if the selection is not exactly one anchor node.

---

### Shortcuts and pickers

```python
anchor.anchor_shortcut()
```
Context-sensitive handler for the `A` keybind. Behaviour depends on the current selection:
- One anchor selected → rename dialog.
- One unanchored Dot selected → Dot anchor promotion (size picker + label prompt).
- Any other nodes selected → create anchor dialog.
- Nothing selected → open the link-creation fuzzy picker.

```python
anchor.select_anchor_and_create()
```
Opens the fuzzy-search picker for link creation. Selecting an entry creates a link node wired to the chosen anchor.

```python
anchor.select_anchor_and_navigate()
```
Opens the fuzzy-search picker for DAG navigation. Selecting an entry pans the DAG view to that anchor.

```python
anchor.navigate_to_anchor(anchor_node: nuke.Node)
```
Pans the DAG view to centre on `anchor_node` without changing the zoom level.

---

### Reconnecting

```python
anchor.reconnect_anchor_node(anchor_node: nuke.Node)
```
Re-wires all link nodes that reference the given anchor. Useful after loading or merging scripts.

```python
anchor.reconnect_all_links()
```
Re-wires every link node in the current script.

---

## Labels (`import labels`)

```python
labels.create_large_label()
```
Prompts for a label and applies it to the selected node with large font sizing. For Dot anchors, propagates the label to all linked nodes.

```python
labels.create_medium_label()
```
Prompts for a label and applies it; Dot nodes get medium font size, other nodes are unchanged. For Dot anchors, propagates the label to all linked nodes.

```python
labels.append_to_label()
```
Prompts for a suffix and appends it to the selected node's existing label. For Dot anchors, propagates the updated label to all linked nodes.

---

## Copy / Paste (`import anchors`)

These are drop-in replacements for Nuke's built-in copy/cut/paste. They are wired to `Ctrl+C/X/V` by `menu.py` automatically on installation. You only need to call them directly if you are building your own menu or keybind setup.

```python
anchors.copy_anchors()
anchors.cut_anchors()
anchors.paste_anchors() -> nuke.Node   # returns last pasted node, same as nuke.nodePaste()
anchors.paste_multiple_anchors()
```

The "old-style" equivalents (no anchor/link magic) are also available as `anchors.copy_old()`, `anchors.cut_old()`, and `anchors.paste_old()`.

### Migration from paste_hidden

If you have existing Nuke scripts (.nk files) created with the old `paste_hidden` plugin,
run the following once per script to migrate the hidden knob names to the new `anchors` format:

```python
import anchors
anchors.migrate_script()
```

This renames the `paste_hidden_dot_anchor` and `paste_hidden_dot_type` knobs on all nodes in
the current script to `anchors_dot_anchor` and `anchors_dot_type`. It prints a summary of
nodes and knobs updated so you can verify the migration. The old knobs are removed after
migration. This operation is not undoable — save a backup of your script first.
