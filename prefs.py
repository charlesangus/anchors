"""Plugin-wide preferences singleton for the anchors plugin.

Loads from ~/.nuke/anchors_prefs.json at import time (once per Nuke session).
Writes via explicit save() call only — called by Phase 7 PrefsDialog on accept.

Module-level variables (read these directly after import):
    plugin_enabled          bool  — True if the plugin is active
    custom_colors           list  — list of 0xRRGGBBAA color ints
    space_mode_order        list  — effective search mode per leading-space count
"""

import json
import os

from constants import (
    DEFAULT_SPACE_MODE_ORDER,
    OLD_PREFS_PATH,
    PREFS_PATH,
    TABTABTAB_PREFS_PATH,
    USER_PALETTE_PATH,
)

# ---------------------------------------------------------------------------
# Defaults — overwritten by _load() at module import time
# ---------------------------------------------------------------------------
plugin_enabled = True
custom_colors = []
naming_regex = ""
naming_template = ""
naming_demo_filename = "plate_v003.exr"
site_config_override = False    # persisted to anchors_prefs.json
last_publish_path = ""          # most recently chosen publish destination; persisted to anchors_prefs.json
keyboard_layout = "qwerty"      # one of "qwerty", "azerty", "qwertz"; persisted to anchors_prefs.json
# Effective search mode for 0, 1 and 2 leading spaces in the fuzzy-find pickers.
# Read this one; it already accounts for use_tabtabtab_prefs.
space_mode_order = list(DEFAULT_SPACE_MODE_ORDER)
use_tabtabtab_prefs = False     # follow a tabtabtab-nuke install's space_mode_order; persisted

_VALID_KEYBOARD_LAYOUTS = ("qwerty", "azerty", "qwertz")
_VALID_SPACE_MODES = frozenset(DEFAULT_SPACE_MODE_ORDER)

# Private — populated by _load_site_config(), never written to user prefs file directly
_site_config = {}               # keys: field names locked by site config; values: admin values
_user_naming_regex = ""         # shadow: user's own saved value for naming_regex
_user_naming_template = ""      # shadow: user's own saved value for naming_template
_user_naming_demo_filename = "plate_v003.exr"  # shadow: user's own saved value for naming_demo_filename
# shadow: user's own saved value for space_mode_order
_user_space_mode_order = list(DEFAULT_SPACE_MODE_ORDER)
# order read from a tabtabtab-nuke install, or None when no install was found
_tabtabtab_space_mode_order = None

_LOCKABLE_NAMING_FIELDS = ('naming_regex', 'naming_template', 'naming_demo_filename')


# Prefs-file and palette migration helpers live in migrations.py so the entire
# legacy → new migration story is in one place.  The thin wrappers below
# preserve the existing _load() call sites without changing semantics.


def _migrate_from_old_palette():
    """Delegate to migrations.migrate_palette_file (kept for back-compat)."""
    import migrations
    migrations.migrate_palette_file()


def _migrate_from_old_prefs_file():
    """Delegate to migrations.migrate_prefs_files (kept for back-compat)."""
    import migrations
    migrations.migrate_prefs_files()


def _load():
    """Load preferences from disk. Called once at module import time.

    If the prefs file does not exist, attempts migration from the old palette
    file. If the prefs file exists but is corrupt or unreadable, silently falls
    back to defaults. Per-key type validation ensures corrupt individual values
    do not poison valid ones.
    """
    global plugin_enabled, custom_colors, \
           naming_regex, naming_template, naming_demo_filename, \
           site_config_override, last_publish_path, \
           keyboard_layout, use_tabtabtab_prefs, \
           _user_naming_regex, _user_naming_template, \
           _user_naming_demo_filename, _user_space_mode_order
    if not os.path.exists(PREFS_PATH):
        _migrate_from_old_prefs_file()
        if not os.path.exists(PREFS_PATH):
            # No old prefs either — try old palette migration
            _migrate_from_old_palette()
            save()
            _load_site_config()
            refresh_tabtabtab_prefs()
            return
        # Old prefs was successfully copied; now fall through to load it
    try:
        with open(PREFS_PATH) as file_handle:
            data = json.load(file_handle)
        if isinstance(data.get('plugin_enabled'), bool):
            plugin_enabled = data['plugin_enabled']
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
        if data.get('keyboard_layout') in _VALID_KEYBOARD_LAYOUTS:
            keyboard_layout = data['keyboard_layout']
        if is_valid_space_mode_order(data.get('space_mode_order')):
            _user_space_mode_order = list(data['space_mode_order'])
        if isinstance(data.get('use_tabtabtab_prefs'), bool):
            use_tabtabtab_prefs = data['use_tabtabtab_prefs']
    except (OSError, ValueError, json.JSONDecodeError):
        pass  # silent fallback — module-level defaults remain
    # Copy user values into shadow vars before site config is applied
    _user_naming_regex = naming_regex
    _user_naming_template = naming_template
    _user_naming_demo_filename = naming_demo_filename
    _load_site_config()
    # Read the tabtabtab-nuke install (if any) and pick the effective mode order
    refresh_tabtabtab_prefs()


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


def is_valid_space_mode_order(candidate_order):
    """Return True when *candidate_order* is a usable space-prefix mode mapping.

    A valid mapping assigns each of the three search modes to exactly one
    leading-space level, matching the rule tabtabtab-nuke's own preferences
    dialog enforces. Anything else (wrong length, unknown mode, duplicate
    mode, not a sequence) is rejected.
    """
    if not isinstance(candidate_order, (list, tuple)):
        return False
    if len(candidate_order) != len(DEFAULT_SPACE_MODE_ORDER):
        return False
    return set(candidate_order) == _VALID_SPACE_MODES


def _tabtabtab_prefs_module():
    """Return the installed tabtabtab-nuke prefs module, or None when absent.

    tabtabtab-nuke ships tabtabtab_prefs.py on NUKE_PATH, so a plain import is
    the most reliable way to tell whether an install is present and where it
    keeps its preferences file.
    """
    try:
        import tabtabtab_prefs
    except Exception:
        return None  # not installed, or an unrelated module of that name failed to import
    return tabtabtab_prefs


def _tabtabtab_prefs_path():
    """Return the path of the tabtabtab-nuke preferences file.

    Prefers the installed module's own PREFS_FILE so a future tabtabtab-nuke
    that relocates its prefs is still followed correctly; falls back to the
    documented default path.
    """
    installed_module = _tabtabtab_prefs_module()
    module_prefs_path = getattr(installed_module, 'PREFS_FILE', None)
    if isinstance(module_prefs_path, str) and module_prefs_path:
        return module_prefs_path
    return TABTABTAB_PREFS_PATH


def refresh_tabtabtab_prefs():
    """Re-read the tabtabtab-nuke space_mode_order and re-apply effective values.

    Sets _tabtabtab_space_mode_order to the order that install is currently
    using, or None when no tabtabtab-nuke install was found. An install that
    has never saved its preferences is still an install: it runs on
    tabtabtab-nuke's defaults, which are the same defaults anchors ships.

    Called at import time, and again whenever the effective order matters, so
    that preferences changed in tabtabtab's own dialog are picked up without a
    Nuke restart.
    """
    global _tabtabtab_space_mode_order
    tabtabtab_prefs_path = _tabtabtab_prefs_path()
    tabtabtab_is_installed = _tabtabtab_prefs_module() is not None
    saved_order = None
    try:
        with open(tabtabtab_prefs_path) as file_handle:
            data = json.load(file_handle)
        if isinstance(data, dict) and is_valid_space_mode_order(data.get('space_mode_order')):
            saved_order = list(data['space_mode_order'])
        tabtabtab_is_installed = True  # a prefs file it wrote is proof enough
    except (OSError, ValueError, json.JSONDecodeError):
        pass  # no readable prefs file — fall back on the install check alone
    if saved_order is not None:
        _tabtabtab_space_mode_order = saved_order
    elif tabtabtab_is_installed:
        _tabtabtab_space_mode_order = list(DEFAULT_SPACE_MODE_ORDER)
    else:
        _tabtabtab_space_mode_order = None
    _apply_effective_space_mode_order()


def tabtabtab_prefs_available():
    """Return True when a tabtabtab-nuke install was found to follow."""
    return _tabtabtab_space_mode_order is not None


def tabtabtab_space_mode_order():
    """Return the tabtabtab-nuke mode order, or the anchors default when absent."""
    if _tabtabtab_space_mode_order is None:
        return list(DEFAULT_SPACE_MODE_ORDER)
    return list(_tabtabtab_space_mode_order)


def _apply_effective_space_mode_order():
    """Set space_mode_order to the effective value.

    Follows the tabtabtab-nuke install when the user asked for it and one was
    found; otherwise uses the user's own saved order.
    """
    global space_mode_order
    if use_tabtabtab_prefs and _tabtabtab_space_mode_order is not None:
        space_mode_order = list(_tabtabtab_space_mode_order)
    else:
        space_mode_order = list(_user_space_mode_order)


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
                'custom_colors': custom_colors,
                'naming_regex': _user_naming_regex,
                'naming_template': _user_naming_template,
                'naming_demo_filename': _user_naming_demo_filename,
                'site_config_override': site_config_override,
                'last_publish_path': last_publish_path,
                'keyboard_layout': keyboard_layout,
                'space_mode_order': list(_user_space_mode_order),
                'use_tabtabtab_prefs': use_tabtabtab_prefs,
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
