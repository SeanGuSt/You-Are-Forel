from objects.object_templates import Node
class NodeGroup:
    def __init__(self, *nodes: Node):
        self._nodes: set[Node] = set()
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
            if not isinstance(node, Node):
                raise TypeError(f"Only Node instances can be added to NodeGroup, got {type(node).__name__}")
            self._nodes.add(node)

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

    def draw(self, surface):
        """Draw all nodes to a given surface (if they have an image)."""
        for node in self._nodes:
            if node.image and node.position:
                surface.blit(node.image, node.position)

    def sprites(self) -> list[Node]:
        """Return a list of all nodes."""
        return list(self._nodes)

    def get_by_name(self, name: str) -> list[Node]:
        """Find nodes by their name."""
        return [node for node in self._nodes if node.name == name]

    def get_at(self, position: tuple[int, int]) -> list[Node]:
        """Get all nodes at a specific tile position."""
        return [node for node in self._nodes if node.position == position]
