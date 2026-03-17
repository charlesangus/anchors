"""Plugin-wide preferences singleton for the anchors plugin.

Loads from ~/.nuke/anchors_prefs.json at import time (once per Nuke session).
Writes via explicit save() call only — called by Phase 7 PrefsDialog on accept.

Module-level variables (read these directly after import):
    plugin_enabled          bool  — True if the plugin is active
    link_classes_paste_mode str   — 'create_link' or 'passthrough'
    custom_colors           list  — list of 0xRRGGBBAA color ints
"""

import json
import os

from constants import OLD_PREFS_PATH, PREFS_PATH, USER_PALETTE_PATH

# ---------------------------------------------------------------------------
# Defaults — overwritten by _load() at module import time
# ---------------------------------------------------------------------------
plugin_enabled = True
link_classes_paste_mode = "create_link"
custom_colors = []
naming_regex = ""
naming_template = ""
naming_demo_filename = "plate_v003.exr"


def _migrate_from_old_palette():
    """One-way migration: read custom colors from old palette file into custom_colors.

    Called only when anchors_prefs.json does not exist.
    Never writes to the old palette file. Silent no-op if old file is absent or corrupt.
    """
    global custom_colors
    try:
        with open(USER_PALETTE_PATH) as file_handle:
            data = json.load(file_handle)
        custom_colors = [int(color_value) for color_value in data
                         if isinstance(color_value, (int, float))]
    except (OSError, ValueError, json.JSONDecodeError):
        custom_colors = []


def _migrate_from_old_prefs_file():
    """One-way migration: copy paste_hidden_prefs.json to anchors_prefs.json.

    Called only when anchors_prefs.json does not exist but paste_hidden_prefs.json does.
    Never modifies the old file. Silent no-op if old file is absent or corrupt.
    """
    global plugin_enabled, link_classes_paste_mode, custom_colors
    if not os.path.exists(OLD_PREFS_PATH):
        return
    try:
        import shutil
        shutil.copy2(OLD_PREFS_PATH, PREFS_PATH)
    except OSError:
        pass


def _load():
    """Load preferences from disk. Called once at module import time.

    If the prefs file does not exist, attempts migration from the old palette
    file. If the prefs file exists but is corrupt or unreadable, silently falls
    back to defaults. Per-key type validation ensures corrupt individual values
    do not poison valid ones.
    """
    global plugin_enabled, link_classes_paste_mode, custom_colors, naming_regex, naming_template, naming_demo_filename
    if not os.path.exists(PREFS_PATH):
        _migrate_from_old_prefs_file()
        if not os.path.exists(PREFS_PATH):
            # No old prefs either — try old palette migration
            _migrate_from_old_palette()
            save()
            return
        # Old prefs was successfully copied; now fall through to load it
    try:
        with open(PREFS_PATH) as file_handle:
            data = json.load(file_handle)
        if isinstance(data.get('plugin_enabled'), bool):
            plugin_enabled = data['plugin_enabled']
        if data.get('link_classes_paste_mode') in ('create_link', 'passthrough'):
            link_classes_paste_mode = data['link_classes_paste_mode']
        if isinstance(data.get('custom_colors'), list):
            custom_colors = [int(color_value) for color_value in data['custom_colors']
                             if isinstance(color_value, (int, float))]
        if isinstance(data.get('naming_regex'), str):
            naming_regex = data['naming_regex']
        if isinstance(data.get('naming_template'), str):
            naming_template = data['naming_template']
        if isinstance(data.get('naming_demo_filename'), str):
            naming_demo_filename = data['naming_demo_filename']
    except (OSError, ValueError, json.JSONDecodeError):
        pass  # silent fallback — module-level defaults remain


def save():
    """Persist current preference values to disk.

    Creates ~/.nuke/ directory if it does not exist.
    Called by Phase 7 PrefsDialog on accept, and automatically on first run to materialize the file.
    """
    os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
    with open(PREFS_PATH, 'w') as file_handle:
        json.dump(
            {
                'plugin_enabled': plugin_enabled,
                'link_classes_paste_mode': link_classes_paste_mode,
                'custom_colors': custom_colors,
                'naming_regex': naming_regex,
                'naming_template': naming_template,
                'naming_demo_filename': naming_demo_filename,
            },
            file_handle,
        )


_load()  # execute at import time — single load per Nuke session
