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

`Ctrl+C`, `Ctrl+X`, and `Ctrl+V` are replaced with hidden-aware versions. Copy stamps a hidden reference knob on the selected nodes; paste reads the reference and reconnects:

- **Link nodes** (hidden-input Dot/PostageStamp/NoOp pointing at an anchor) — paste re-pipes the link to the original anchor when the anchor is reachable in the same script. If the anchor is missing (cross-script paste), the link falls back to looking up an anchor with the same display name in the destination script.
- **Local Dots** (hidden-input Dot whose source is a plain node, not an anchor) — paste re-pipes by node identity inside the same script only. Cross-script pastes are silently left disconnected; Local Dots never look up by name.
- **Anchors pasted from a clipboard whose entire selection was anchors** — each pasted anchor is automatically replaced by a Link node pointing back at the original anchor (cut + paste skips this so cuts move anchors cleanly).
- **Paste Multiple** (`Edit > Paste Multiple`) pastes the clipboard contents multiple times in sequence, with full hidden-input re-piping applied each time.
- **Old-style paste** (no re-piping magic): `Edit > Anchors > Paste (old)` / `Ctrl+Shift+D`. Old-style copy and cut are also available under `Edit > Anchors`.

When the plugin is disabled in Preferences, `Ctrl+C/X/V` fall through to plain `nuke.nodeCopy` / `nuke.nodePaste`.

# Anchor System

The anchor system is a reusable named-input mechanism for the node graph.

## Concepts

- **Anchor** — a named NoOp (node name prefixed `Anchor_`) or labelled Dot node that sits below an input node and acts as a stable reference point. NoOp anchors carry "Reconnect Child Links", "Rename", and "Set Color" buttons in their properties panel; Dot anchors carry only "Reconnect Child Links" and "Rename".
- **Link** — a PostageStamp, NoOp, or Dot node that references an anchor by fully-qualified name. Carries a "Reconnect" button and re-pipes itself when reconnected. Displays a `Link: <name>` label.
- **Local Dot** — a hidden-input Dot used purely for layout cleanup. Created automatically when a hidden-input Dot is copied whose upstream is a plain node (not an anchor). Reconnects same-script only and never crosses scripts. Stamped with a burnt-orange tile color and a `Local: <source>` label.

## Creating Anchors

- Select a node and press `A` (or `Edit > Anchors > Create Anchor`) — a combined name + color dialog appears, pre-filled from the input node's file path and the smallest containing backdrop label.
- **Dot anchors**: select a plain Dot and press `Shift+B`, `Shift+N`, or `Shift+M`. The label prompt appears; entering a label and confirming applies a small/medium/large font and promotes the Dot to a Dot anchor in place.
- **Rename**: if an anchor is already selected when you press `A`, the rename dialog opens instead of creating a new anchor.

## Creating Links

- With no node selected, press `A` (or `Edit > Anchors > Create Link`) — a fuzzy-search picker appears listing all anchors with their colors. Pick one and a link node is created and wired.

## Renaming

- Select an anchor and press `A` — the rename dialog opens, pre-filled with the current name (NoOp anchors) or label (Dot anchors).
- Or: `Edit > Anchors > Rename Anchor`.
- All link nodes referencing the anchor are updated automatically.

## Navigating

- `Alt+A` (or `Edit > Anchors > Anchor Find`) — fuzzy-search picker listing every anchor and every labelled BackdropNode. Selecting an entry zooms the DAG to it.
- `Alt+J` (or `Edit > Anchors > Anchor Jump`) — with a Link selected, jump to its source anchor.
- `Alt+L` (or `Edit > Anchors > Cycle Links`) — with an anchor selected, cycle through each Link node that references it. After the last one, returns to the anchor.
- `Alt+Z` (or `Edit > Anchors > Anchor Back`) — restore the DAG viewport to the position before the last Alt+A / Alt+J / Alt+L jump. Single-slot — consumes the saved position.

## Leader Key

`Shift+A` opens the **leader key** overlay — a translucent HUD that surfaces every anchor command as a single follow-up keystroke, with cells laid out to match your physical keyboard.

Press `Shift+A`, then one of the keys below:

| Key | Action |
|---|---|
| `Q` | Set B Input To… (opens picker; wires the new link to input 0 of the selected node, replacing whatever was there) |
| `W` | Set A Input To… (input 1) |
| `E` | Set Mask Input To… (input 2 on Merge-style multi-input nodes — `maxInputs() > 100` — last input on everything else) |
| `R` | Set First Free Input To… (lowest free slot only — never overwrites existing wiring) |
| `F` | Anchor Find (same as `Alt+A`) |
| `J` | Anchor Jump (same as `Alt+J`) |
| `L` | Cycle Links (same as `Alt+L`) — *chaining*: stays armed so repeated `L` advances through the cycle. Any other key or a mouse click disarms. |
| `Z` | Anchor Back (same as `Alt+Z`) |
| `X` | Reconnect All Links |
| `,` | Anchor Preferences |

Cells grey out when their precondition isn't met for the current selection — e.g. `W` greys on a single-input node, `E` greys when no mask input exists, `R` greys when every slot is filled, `J` greys unless a Link is selected, `L` greys unless an anchor is selected, `Z` greys unless there's a saved jump-back position. Pressing a greyed key disarms the leader silently.

Set your keyboard layout in `Edit > Anchors > Anchor Preferences…` (QWERTY, AZERTY, or QWERTZ). The overlay then renders the letter actually printed on your physical key — so on AZERTY the `Q` cell shows `A`, while still triggering the same Set-B-Input action.

When the plugin is disabled in Preferences, the `Shift+A` shortcut is disabled along with every other gated anchor command. Re-enable from `Edit > Anchors > Anchor Preferences…`, which stays active in the menu.

The existing `Alt+A`, `Alt+J`, `Alt+L`, `Alt+Z` shortcuts continue to work alongside the leader for muscle-memory parity.

## Reconnecting

- `Edit > Anchors > Reconnect All Links` — re-wires all link nodes in the script. Useful after a script load or merge.
- The "Reconnect Child Links" button on each anchor node re-wires only that anchor's links.
- The "Reconnect" button on each Link node re-wires that single Link.

## Colors

Anchors inherit their tile color automatically using this priority:

1. The smallest containing BackdropNode — when the anchor's input lives inside one (any input node type, not just Read).
2. The input node's tile color (with Nuke Preferences fallback).
3. Default purple (`#6f3399`) if neither is available.

NoOp anchors carry a "Set Color" button in their properties panel that opens the color palette dialog (preset + custom colors). Dot anchors are excluded from the color system — they always use the default purple.

Link nodes inherit the same color as their anchor and update automatically when the anchor's color is changed.

## Auto-Naming

The suggested anchor name is derived from the input node's `file` knob. By default, the basename is taken, any trailing `_v<number>` version suffix and file extension (and frame tokens like `%04d` / `####`) are stripped, and the result is prefixed with the smallest containing backdrop's label (if any).

This default can be overridden via a user-configurable regex + template pair set in `Edit > Anchors > Anchor Preferences...`. Sites can ship a locked default by writing a JSON file with `naming_regex`, `naming_template`, and `naming_demo_filename` keys and pointing the `ANCHORS_SITE_CONFIG` environment variable at it. Users can override the site config via the "Override Site Config" checkbox in Preferences. Admins can publish their current naming settings to a site config file via the "Publish Naming…" button in Preferences.

# Label Utilities

Keyboard shortcuts for quickly labelling Dot anchors and other nodes (available under `Edit > Anchors`):

| Shortcut | Action |
|---|---|
| `Shift+M` | Label (Large) — prompts for a label; applies large font (111) to Dots and large font (33) to other nodes |
| `Shift+N` | Label (Medium) — prompts for a label; applies medium font (66) to Dots, unchanged for other nodes |
| `Shift+B` | Label (Small) — prompts for a label; applies small font (33) to Dots, unchanged for other nodes |
| `Ctrl+M` | Append Label — prompts for a suffix and appends it to the existing label |

All three Label shortcuts apply a font size at or above the Dot-anchor threshold (33pt), so labelling a plain Dot via any of them promotes it to a Dot anchor.

For Dot anchors, applying or appending a label also propagates the change to all link nodes pointing at that Dot.

# Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+C` | Copy (hidden) |
| `Ctrl+X` | Cut (hidden) |
| `Ctrl+V` | Paste (hidden) |
| `Ctrl+Shift+D` | Paste (old-style, no re-piping) |
| `A` | Anchor shortcut (context-sensitive: create anchor, rename, or open link picker) |
| `Shift+A` | Leader Key — opens the command overlay (see Leader Key section above) |
| `Alt+A` | Anchor Find (navigate DAG to any anchor or labelled BackdropNode) |
| `Alt+J` | Anchor Jump (Link → source anchor) |
| `Alt+L` | Cycle Links (anchor → each referencing Link) |
| `Alt+Z` | Anchor Back (restore previous DAG position) |
| `Shift+M` | Label (Large) |
| `Shift+N` | Label (Medium) |
| `Shift+B` | Label (Small) |
| `Ctrl+M` | Append Label |

All anchor shortcuts are scoped to the **DAG (Node Graph) context** — they only fire when the Node Graph has focus. This keeps them from intercepting keys (e.g. `Ctrl+C/X/V`) while you're typing in the Script Editor, Viewer, or other panels.

# Preferences

`Edit > Anchors > Anchor Preferences...` opens a dialog with:

- **Enable anchors plugin** — master toggle. When unchecked, all gated menu items disable and `Ctrl+C/X/V` fall through to plain Nuke copy/cut/paste.
- **Custom Colors** — a palette of user-defined colors. Available in the anchor create / rename dialogs and in the "Set Color" picker on NoOp anchors.
- **Anchor Naming (Advanced)** — user-configurable regex + template for deriving anchor names from file paths. Includes a live preview against a test filename and an "Override Site Config" checkbox. Admins can publish the current values to a site config JSON via the "Publish Naming…" button.

Preferences are persisted to `~/.nuke/anchors_prefs.json`.

# Configuration

Edit `constants.py` to change low-level defaults:

- **`HIDDEN_INPUT_CLASSES`** — list of node classes that are treated as hidden-input proxies (default: `PostageStamp`, `Dot`, `NoOp`).
- **`ANCHOR_PREFIX` / `DOT_ANCHOR_PREFIX`** — node-name prefixes used to identify anchors (default: `Anchor_` and `Anchor_Dot_`). FROZEN: changing these breaks loading of existing scripts.
- **`ANCHOR_DEFAULT_COLOR`** / **`LOCAL_DOT_COLOR`** — fallback tile colors (default purple `#6f3399` for anchors, burnt orange `#7A3A00` for Local Dots).
- **Font sizes** — `DOT_LABEL_FONT_SIZE_{LARGE,MEDIUM,SMALL}`, `DOT_LINK_LABEL_FONT_SIZE`, `DOT_ANCHOR_MIN_FONT_SIZE` (the threshold above which an unprefixed labelled Dot is treated as a Dot anchor).

The link node class is determined automatically: a Dot source produces a Dot link; everything else produces a NoOp link.

# Python API

For external pipeline tools and templating systems, the **stable public surface** is `api.py`:

```python
from api import create_anchor, find_anchor_by_name

bg_read = nuke.toNode('Read_BG')
existing = find_anchor_by_name('BG_Plate')
if existing is None:
    anchor_node = create_anchor('BG_Plate', input_node=bg_read, color=0x8040FFFF)
```

The two functions in `api.py` are thin wrappers over `anchor.create_anchor_named` / `anchor.find_anchor_by_name` and are guaranteed to keep their signatures stable. Both raise `RuntimeError` when called outside a running Nuke session.

The functions documented below in `anchor`, `anchors`, and `labels` are the internal entry points used by `menu.py`. They are usable directly but are not part of the stable public API.

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
Creates a link node wired to the given anchor node and returns it. The link is a Dot when the anchor is a Dot anchor, and a NoOp otherwise.

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
- Any other selection → create-anchor dialog (combined name + color).
- Nothing selected → open the link-creation fuzzy picker.

Note: promoting a plain Dot to a Dot anchor is a separate flow — use `Shift+B/N/M` (the label shortcuts) to apply a font ≥33pt, which marks the Dot as an anchor in place.

```python
anchor.select_anchor_and_create()
```
Opens the fuzzy-search picker for link creation. Selecting an entry creates a link node wired to the chosen anchor.

```python
anchor.select_anchor_and_navigate()
```
Opens the fuzzy-search picker for DAG navigation. Lists all anchors plus all labelled BackdropNodes. Selecting an entry zooms the DAG to fit it.

```python
anchor.navigate_to_anchor(anchor_node: nuke.Node)
```
Zooms the DAG to fit the anchor and its visible-path upstream nodes.

```python
anchor.navigate_back()
```
Restores the DAG viewport to the position saved before the most recent jump (Alt+A / Alt+J / Alt+L). Single-slot — consumes the saved position.

```python
anchor.jump_to_selected_anchor()
```
With a Link node selected, jumps the DAG to the source anchor. Saves the current viewport first.

```python
anchor.cycle_next_link()
```
With an anchor selected, cycles through each Link node referencing it. Saves the viewport on first invocation; after the last Link, returns to the anchor.

```python
anchor.create_links_from_selected_anchors()
```
For each selected anchor, creates a wired Link node placed to the right of the anchor.

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

### Coloring

```python
anchor.set_anchor_color(anchor_node: nuke.Node)
```
Opens the color palette dialog and applies the chosen color to the anchor and all its Link nodes. No-op for Dot anchors. This is the entry point called by the "Set Color" button on each anchor's properties panel.

```python
anchor.propagate_anchor_color(anchor_node: nuke.Node, color_int: int)
```
Sets the anchor's `tile_color` to `color_int` (0xRRGGBBAA) and propagates the same color to every Link node referencing it. No-op for Dot anchors.

---

## Labels (`import labels`)

```python
labels.create_large_label()
```
Prompts for a label and applies it. Dot nodes get a 111pt font and other nodes get a 33pt font. For Dot anchors, propagates the label to all linked nodes.

```python
labels.create_medium_label()
```
Prompts for a label and applies it. Dot nodes get a 66pt font; other nodes are unchanged. For Dot anchors, propagates the label to all linked nodes.

```python
labels.create_small_label()
```
Prompts for a label and applies it. Dot nodes get a 33pt font (the Dot-anchor threshold); other nodes are unchanged. For Dot anchors, propagates the label to all linked nodes.

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

`anchors.migrate_script()` rewrites every legacy hidden knob on every node in the current script (recursing into Groups) to the unified `anchors_*` namespace. It is idempotent — re-running on already-migrated state is a no-op — and is registered via `nuke.addOnScriptLoad`, so opened scripts are migrated automatically before any code path reads the new constants.

The legacy → new knob mapping covers:

| Legacy knob | New knob |
|---|---|
| `copy_hidden_tab` | `anchors_tab` |
| `copy_hidden_input_node` | `anchors_input_node` |
| `paste_hidden_dot_anchor` | `anchors_dot_anchor` |
| `paste_hidden_dot_type` | `anchors_dot_type` |
| `reconnect_link` | `anchors_reconnect_link` |
| `reconnect_child_links` | `anchors_reconnect_child_links` |
| `rename_anchor` | `anchors_rename_anchor` |
| `set_anchor_color` | `anchors_set_anchor_color` |

A second migrator, available from `Edit > Anchors > Anchor Migrate from Old Version`, calls `anchors.migrate_to_stemless_names()`. This rewrites stored anchor references on link nodes from the very-old `scriptStem.fullName` format (e.g. `myScript.Anchor_Foo`) to the current `fullName`-only format (e.g. `Anchor_Foo` or `Group1.Anchor_Foo`). It is safe to run on already-migrated scripts (no-op).

Both migrators print a summary of the nodes/knobs updated. Neither is undoable — save a backup of your script first.

# Development

## Setup

After cloning, activate the pre-commit hook (runs the same tests as CI):

```sh
git config core.hooksPath .githooks
```

## Running tests

```sh
pytest tests/
```
