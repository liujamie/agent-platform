"""tests/test_workflow_graph.py"""
import pytest
from app.models.workflow import NodeDef, EdgeDef, NodeType, RetryConfig
from app.core.workflow.graph import WorkflowGraph, CyclicGraphError, NodeNotFoundError


class TestWorkflowGraph:
    def test_empty_graph(self):
        g = WorkflowGraph()
        assert g.node_count() == 0
        assert g.edge_count() == 0

    def test_add_node(self):
        g = WorkflowGraph()
        node = NodeDef(id="a", type=NodeType.agent, config={})
        g.add_node(node)
        assert g.node_count() == 1

    def test_add_duplicate_node_raises(self):
        g = WorkflowGraph()
        node = NodeDef(id="a", type=NodeType.agent, config={})
        g.add_node(node)
        with pytest.raises(ValueError, match="already exists"):
            g.add_node(node)

    def test_add_edge(self):
        g = WorkflowGraph()
        g.add_node(NodeDef(id="a", type=NodeType.agent, config={}))
        g.add_node(NodeDef(id="b", type=NodeType.agent, config={}))
        g.add_edge("a", "b")
        assert g.edge_count() == 1

    def test_add_edge_to_nonexistent_node_raises(self):
        g = WorkflowGraph()
        g.add_node(NodeDef(id="a", type=NodeType.agent, config={}))
        with pytest.raises(NodeNotFoundError):
            g.add_edge("a", "z")

    def test_topo_sort_single_node(self):
        g = WorkflowGraph()
        g.add_node(NodeDef(id="a", type=NodeType.agent, config={}))
        layers = g.topo_sort()
        assert layers == [["a"]]

    def test_topo_sort_linear(self):
        g = WorkflowGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(NodeDef(id=nid, type=NodeType.agent, config={}))
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        layers = g.topo_sort()
        assert layers == [["a"], ["b"], ["c"]]

    def test_topo_sort_parallel(self):
        g = WorkflowGraph()
        for nid in ["a", "b", "c", "d"]:
            g.add_node(NodeDef(id=nid, type=NodeType.agent, config={}))
        g.add_edge("a", "b")
        g.add_edge("a", "c")
        g.add_edge("b", "d")
        g.add_edge("c", "d")
        layers = g.topo_sort()
        assert layers[0] == ["a"]
        assert set(layers[1]) == {"b", "c"}
        assert layers[2] == ["d"]

    def test_cyclic_graph_raises(self):
        g = WorkflowGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(NodeDef(id=nid, type=NodeType.agent, config={}))
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "a")
        with pytest.raises(CyclicGraphError):
            g.topo_sort()

    def test_get_node(self):
        g = WorkflowGraph()
        node = NodeDef(id="a", type=NodeType.agent, config={})
        g.add_node(node)
        assert g.get_node("a") is node

    def test_get_nonexistent_node(self):
        g = WorkflowGraph()
        assert g.get_node("z") is None

    def test_get_children(self):
        g = WorkflowGraph()
        g.add_node(NodeDef(id="a", type=NodeType.agent, config={}))
        g.add_node(NodeDef(id="b", type=NodeType.agent, config={}))
        g.add_node(NodeDef(id="c", type=NodeType.agent, config={}))
        g.add_edge("a", "b")
        g.add_edge("a", "c")
        children = g.get_children("a")
        assert set(children) == {"b", "c"}

    def test_node_with_retry_config(self):
        retry = RetryConfig(max_retries=5, backoff_seconds=2.0)
        node = NodeDef(id="a", type=NodeType.agent, config={}, retry=retry)
        g = WorkflowGraph()
        g.add_node(node)
        assert g.get_node("a").retry.max_retries == 5
