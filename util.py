import nuke
import nukescripts


def upstream_ignoring_hidden(node, nodes_so_far=None, _visited=None):
    if _visited is None:
        _visited = set()
    if node in _visited:
        return nodes_so_far
    _visited.add(node)

    inputs = node.dependencies(what=nuke.INPUTS)
    if not inputs:
        return nodes_so_far
    if nodes_so_far is None:
        nodes_so_far = set(inputs)
    else:
        nodes_so_far.update(inputs)
    for input_node in inputs:
        upstream_ignoring_hidden(input_node, nodes_so_far, _visited)
    return nodes_so_far


def select_upstream_ignoring_hidden():
    node = nuke.selectedNode()
    ns = upstream_ignoring_hidden(node)
    nukescripts.clear_selection_recursive()
    for n in ns:
        n["selected"].setValue(True)
    node["selected"].setValue(True)
