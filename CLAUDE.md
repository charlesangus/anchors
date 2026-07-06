# Project instructions for the anchors plugin

## Keep documentation and screenshots in sync with the code

The user-facing documentation is a single guide: `docs/user-guide.md`, its
screenshots in `docs/img/`, and the generated PDF `docs/anchors-user-guide.pdf`.
It is part of the deliverable and **must be kept current with every change to the
codebase.** The docs are generated **locally and committed** — CI does not build
them (capturing the screenshots needs a licensed Nuke plus every gizmo the example
comps reference). Both `docs/img/*.png` and `docs/anchors-user-guide.pdf` are
checked in; the release workflow bundles the PDF.

When you change anything a user can see — behaviour, UI, dialogs, menu entries,
keyboard shortcuts, node names/labels, colours, or the public API in `api.py` —
in the same change you must:

1. Update the affected prose in `docs/user-guide.md`.
2. Update the screenshot sources if the change affects what a screenshot depicts:
   the hand-crafted example comps `docs/examples-problems-solution.nk` and
   `docs/examples-workflows.nk`, the reconnect fixture
   `docs/screenshots/fixtures/anchors_dag.nk`, the playback scenarios in
   `scenarios/gui.json`, or the capture helper in `nuke_path/menu.py`.
3. Regenerate with **`make`** (or `make screenshots` / `make pdf` for one stage)
   on a workstation with Nuke and the toolchain, and commit the updated
   `docs/img/*.png` and `docs/anchors-user-guide.pdf`.

Do not hand-edit files in `docs/img/` — they are generated.

### How the screenshots are generated

`make screenshots` drives a real Nuke session via
[nuke-screenshotter](https://github.com/charlesangus/nuke-screenshotter) in two
modes:

- **DAG screenshots** — captured from **hand-crafted** `.nk` sources: the two
  example comps (`docs/examples-*.nk`) that carry the narrative, plus the reconnect
  fixture (`docs/screenshots/fixtures/anchors_dag.nk`). These `.nk` files are
  committed source: edit them by hand; `make` never regenerates them. The
  screenshotter captures one PNG per `BackdropNode` whose `label` starts with
  `screenshot:` (the PNG is named after the slugified remainder — hyphens and
  spaces become underscores, e.g. `screenshot: dot-anchors` → `dot_anchors.png`).
  Comps follow a clean vertical **B-spine** (a node's main input runs straight
  down; secondary inputs join from the right). Rendering notes:
  - Node **names, labels, and autolabels render** (the tool warms up each node at
    the render zoom to force full-label drawing), as do **Dot note-labels** (the
    large `Shift`+`B`/`N`/`M` captions) and tile colours.
  - **BackdropNode label text does *not* render** — a backdrop shows its node
    *name* — so a coloured input-block backdrop reads by colour, not label.
  - Labels are drawn only while the dot/node is on-screen in a capture tile, so an
    off-screen dot's label can be dropped at a tile seam. Keep Dot captions short
    (e.g. `fg`, not `plate over cg`).
- **GUI screenshots** — `scenarios/gui.json` replays GUI actions (overlay, pickers,
  dialogs) and captures the Qt widgets, where text renders normally. The doc-only
  helper `nuke_path/menu.py` (on `NUKE_PATH` only during generation, never shipped)
  loads `docs/examples-workflows.nk` so the `A` / `Alt+A` pickers list the guide's
  real anchors, and shows the otherwise-modal `ColorPaletteDialog` non-modally.

Requirements: a licensed interactive Nuke plus `xvfb-run`, `pandoc`, and `xelatex`
on the host. The screenshotter location is overridable via `SCREENSHOTTER_DIR`.

### How the PDF is built

`make pdf` renders `docs/user-guide.md` through pandoc using the studio training
document class in `docs/latex/` (`training_doc.cls` + `logo.pdf`) via the pandoc
template `docs/latex/template.tex`, writing `docs/anchors-user-guide.pdf`. The
Makefile sets `TEXINPUTS` so the engine finds the class and logo. Images are
**non-floating, numbered figures** placed exactly where written: the template
makes each pandoc `figure` an in-place block captioned via `\@captype`/`\caption`
(no `float` package, no `[H]` — a float is a float and would drift). Each image
carries a `{#fig:...}` id and the prose refers to it with a raw-LaTeX
`` `(Figure \ref{fig:...})`{=latex} `` span, which renders as "(Figure N)" in the
PDF and disappears in Markdown (GitHub does not number figures). Edit the class or
template to change PDF styling; do not pass conflicting `-V geometry`/font options
(the class owns fonts and geometry).
