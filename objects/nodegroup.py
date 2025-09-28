from objects.object_templates import Node
class NodeGroup:
    def __init__(self, *nodes: Node):
        self._nodes: list[Node] = []
        self.progress = 0
        self.name = ""
        self.checked_movement = False
        if nodes:
            self.add(*nodes)

    def __iter__(self):
        return iter(self._nodes)

    def __len__(self):
        return len(self._nodes)

    def __contains__(self, node: Node):
        return node in self._nodes

    def add(self, *nodes: Node):
        """Add one or more Node instances to the group."""
        for node in nodes:
            if not self.name:
                self.name = node.group_name
            elif node.group_name != self.name:
                raise Exception(f"Cannot add {node.name} to NodeGroup {self.name}. It belongs to {node.group_name}.")
            if not isinstance(node, Node):
                raise TypeError(f"Only Node instances can be added to NodeGroup, got {type(node).__name__}")
            self._nodes.append(node)

    def remove(self, *nodes: Node):
        """Remove one or more Node instances from the group."""
        for node in nodes:
            self._nodes.discard(node)

    def clear(self):
        """Remove all nodes from the group."""
        self._nodes.clear()

    def update(self, **kwargs):
        """Call each node's update method with optional kwargs."""
        for node in list(self._nodes):
            node.update(**kwargs)

    def get_by_name(self, name: str) -> list[Node]:
        """Find nodes by their name."""
        return [node for node in self._nodes if node.name == name]

    def get_at(self, position: tuple[int, int]) -> list[Node]:
        """Get all nodes at a specific tile position."""
        return [node for node in self._nodes if node.position == position]
