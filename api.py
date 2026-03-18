"""Public API for the anchors system.

Provides a stable, documented interface for external Nuke templating systems to
create and look up anchor nodes without reaching into private internals.

Intended to be imported from .nuke/init.py or from pipeline scripts that run
inside a live Nuke session:

    from api import create_anchor, find_anchor_by_name

Examples
--------
Create an anchor programmatically from a templating system:

    >>> bg_read = nuke.toNode('Read_BG')
    >>> anchor_node = create_anchor('BG_Plate', input_node=bg_read, color=0x8040FFFF)

Look up an existing anchor by its display name before creating a duplicate:

    >>> existing = find_anchor_by_name('BG_Plate')
    >>> if existing is None:
    ...     anchor_node = create_anchor('BG_Plate')
"""

import sys

import anchor


def _assert_nuke_session():
    """Raise RuntimeError if nuke is not present in sys.modules.

    This guards every public function so callers get a clear error message when
    the API is used outside a running Nuke session (e.g., in an offline script).
    """
    if 'nuke' not in sys.modules:
        raise RuntimeError('anchors API requires a running Nuke session')


def create_anchor(name, input_node=None, color=None):
    """Create a named anchor node in the current Nuke script.

    Thin wrapper over ``anchor.create_anchor_named`` that provides a stable
    public surface for external callers.

    Parameters
    ----------
    name : str
        Display name for the anchor.  Special characters are sanitized
        automatically; raises ``ValueError`` if the result is an empty string.
    input_node : nuke.Node or None
        Optional node to connect the anchor to and position it below.
    color : int or None
        Explicit tile color as a 0xRRGGBBAA integer.  If ``None``, the color is
        derived automatically from the anchor name.

    Returns
    -------
    nuke.Node
        The newly created anchor node.

    Raises
    ------
    ValueError
        If *name* sanitizes to an empty string (e.g., ``'!!!'``).
    RuntimeError
        If nuke is not available in the current Python session.

    Examples
    --------
    Create an anchor connected to an existing node with an explicit color:

        >>> source_node = nuke.toNode('Read1')
        >>> anchor_node = create_anchor('BG_Plate', input_node=source_node, color=0x8040FFFF)

    Create a simple named anchor with automatic color:

        >>> anchor_node = create_anchor('OutputPass')
    """
    _assert_nuke_session()
    return anchor.create_anchor_named(name, input_node, color)


def find_anchor_by_name(display_name):
    """Return the anchor node whose display name matches *display_name*, or None.

    Thin wrapper over ``anchor.find_anchor_by_name`` that provides a stable
    public surface for external callers.

    Parameters
    ----------
    display_name : str
        The display name to search for.  Comparison is case-sensitive.

    Returns
    -------
    nuke.Node or None
        The first anchor node whose display name equals *display_name*, or
        ``None`` if no such anchor exists in the current script.

    Raises
    ------
    RuntimeError
        If nuke is not available in the current Python session.

    Examples
    --------
    Look up an anchor before creating a duplicate:

        >>> existing = find_anchor_by_name('BG_Plate')
        >>> if existing is None:
        ...     existing = create_anchor('BG_Plate')
    """
    _assert_nuke_session()
    return anchor.find_anchor_by_name(display_name)


__all__ = ['create_anchor', 'find_anchor_by_name']
