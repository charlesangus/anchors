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
site_config_override = False    # persisted to anchors_prefs.json
last_publish_path = ""          # most recently chosen publish destination; persisted to anchors_prefs.json

# Private — populated by _load_site_config(), never written to user prefs file directly
_site_config = {}               # keys: field names locked by site config; values: admin values
_user_naming_regex = ""         # shadow: user's own saved value for naming_regex
_user_naming_template = ""      # shadow: user's own saved value for naming_template
_user_naming_demo_filename = "plate_v003.exr"  # shadow: user's own saved value for naming_demo_filename

_LOCKABLE_NAMING_FIELDS = ('naming_regex', 'naming_template', 'naming_demo_filename')


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
    global plugin_enabled, link_classes_paste_mode, custom_colors, \
           naming_regex, naming_template, naming_demo_filename, \
           site_config_override, last_publish_path, \
           _user_naming_regex, _user_naming_template, \
           _user_naming_demo_filename
    if not os.path.exists(PREFS_PATH):
        _migrate_from_old_prefs_file()
        if not os.path.exists(PREFS_PATH):
            # No old prefs either — try old palette migration
            _migrate_from_old_palette()
            save()
            _load_site_config()
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
        if isinstance(data.get('site_config_override'), bool):
            site_config_override = data['site_config_override']
        if isinstance(data.get('last_publish_path'), str):
            last_publish_path = data['last_publish_path']
    except (OSError, ValueError, json.JSONDecodeError):
        pass  # silent fallback — module-level defaults remain
    # Copy user values into shadow vars before site config is applied
    _user_naming_regex = naming_regex
    _user_naming_template = naming_template
    _user_naming_demo_filename = naming_demo_filename
    _load_site_config()


def _load_site_config():
    """Read ANCHORS_SITE_CONFIG env var and load the site config file.

    Populates _site_config with field names present in the JSON file.
    Sets effective module-level naming vars based on site config + override state.
    Silent no-op when env var unset, file missing, or file corrupt.
    """
    global _site_config, naming_regex, naming_template, naming_demo_filename
    _site_config = {}
    site_config_path = os.environ.get("ANCHORS_SITE_CONFIG", "")
    if not site_config_path:
        return
    try:
        with open(site_config_path) as file_handle:
            data = json.load(file_handle)
        for field_name in _LOCKABLE_NAMING_FIELDS:
            if isinstance(data.get(field_name), str):
                _site_config[field_name] = data[field_name]
    except (OSError, ValueError, json.JSONDecodeError):
        return  # silent fallback — _site_config stays empty
    _apply_effective_naming_values()


def _apply_effective_naming_values():
    """Set module-level naming vars to effective values.

    When a field is locked by site config AND override is off: use site config value.
    Otherwise: use user's own saved value.
    """
    global naming_regex, naming_template, naming_demo_filename
    if not site_config_override:
        naming_regex = _site_config.get('naming_regex', _user_naming_regex)
        naming_template = _site_config.get('naming_template', _user_naming_template)
        naming_demo_filename = _site_config.get('naming_demo_filename', _user_naming_demo_filename)
    else:
        naming_regex = _user_naming_regex
        naming_template = _user_naming_template
        naming_demo_filename = _user_naming_demo_filename


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
                'naming_regex': _user_naming_regex,
                'naming_template': _user_naming_template,
                'naming_demo_filename': _user_naming_demo_filename,
                'site_config_override': site_config_override,
                'last_publish_path': last_publish_path,
            },
            file_handle,
        )


def publish(destination_path):
    """Write only naming fields to destination_path in sparse site config format.

    Writes the currently effective naming values (naming_regex, naming_template,
    naming_demo_filename module vars). Called by PrefsDialog._on_publish_naming()
    which flushes field values before calling this.
    Creates parent directories if they do not exist.
    Does not change any module-level variables or call save().
    """
    parent_directory = os.path.dirname(destination_path)
    if parent_directory:
        os.makedirs(parent_directory, exist_ok=True)
    with open(destination_path, 'w') as file_handle:
        json.dump(
            {
                'naming_regex': naming_regex,
                'naming_template': naming_template,
                'naming_demo_filename': naming_demo_filename,
            },
            file_handle,
        )


_load()  # execute at import time — single load per Nuke session
