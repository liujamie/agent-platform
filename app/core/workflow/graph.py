from collections import deque

from app.models.workflow import NodeDef, EdgeDef


class NodeNotFoundError(Exception):
    pass


class CyclicGraphError(Exception):
    pass


class WorkflowGraph:
    """Directed Acyclic Graph for workflow orchestration."""

    def __init__(self):
        self._nodes: dict[str, NodeDef] = {}
        self._edges: list[EdgeDef] = []
        self._adjacency: dict[str, list[str]] = {}

    def add_node(self, node: NodeDef) -> None:
        if node.id in self._nodes:
            raise ValueError(f"Node '{node.id}' already exists")
        self._nodes[node.id] = node
        self._adjacency[node.id] = []

    def add_edge(self, source: str, target: str, condition: str | None = None) -> None:
        if source not in self._nodes:
            raise NodeNotFoundError(f"Source node '{source}' not found")
        if target not in self._nodes:
            raise NodeNotFoundError(f"Target node '{target}' not found")
        self._edges.append(EdgeDef(source=source, target=target, condition=condition))
        self._adjacency.setdefault(source, []).append(target)

    def get_node(self, node_id: str) -> NodeDef | None:
        return self._nodes.get(node_id)

    def get_children(self, node_id: str) -> list[str]:
        return list(self._adjacency.get(node_id, []))

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def topo_sort(self) -> list[list[str]]:
        """
        Kahn's algorithm: return nodes grouped by layer.
        Each inner list can be executed in parallel.
        """
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        for src in self._adjacency:
            for tgt in self._adjacency[src]:
                in_degree[tgt] = in_degree.get(tgt, 0) + 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        layers: list[list[str]] = []
        visited_count = 0

        while queue:
            layer = []
            for _ in range(len(queue)):
                nid = queue.popleft()
                layer.append(nid)
                visited_count += 1
                for child in self._adjacency.get(nid, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)
            layers.append(layer)

        if visited_count != len(self._nodes):
            raise CyclicGraphError("Graph contains a cycle")

        return layers
