"""tests/test_observability.py"""
import pytest
from app.observability.tracer import Tracer, TraceSpan
from app.observability.metrics import MetricsCollector


class TestTracer:
    def test_create_trace(self):
        tracer = Tracer()
        trace = tracer.create_trace("agent", "test-agent")
        assert trace.trace_id is not None
        assert len(trace.spans) == 0

    def test_add_span(self):
        tracer = Tracer()
        trace = tracer.create_trace("agent", "test-agent")
        span = tracer.add_span(
            trace.trace_id, node_id="step1", node_type="llm_call",
            status="success", duration_ms=100,
        )
        assert span.span_id is not None
        assert span.node_id == "step1"

    def test_get_trace(self):
        tracer = Tracer()
        trace = tracer.create_trace("agent", "test-agent")
        retrieved = tracer.get_trace(trace.trace_id)
        assert retrieved is trace

    def test_get_nonexistent_trace(self):
        tracer = Tracer()
        assert tracer.get_trace("nonexistent") is None

    def test_span_with_parent(self):
        tracer = Tracer()
        trace = tracer.create_trace("workflow", "wf-1")
        parent = tracer.add_span(trace.trace_id, "parent", "agent", "success", 50)
        child = tracer.add_span(trace.trace_id, "child", "tool", "success", 30, parent_span_id=parent.span_id)
        assert child.parent_span_id == parent.span_id


class TestMetricsCollector:
    def test_increment_counter(self):
        mc = MetricsCollector()
        mc.increment("requests", {"status": "success"})
        assert mc.get_counter("requests", {"status": "success"}) == 1

    def test_increment_counter_multiple(self):
        mc = MetricsCollector()
        mc.increment("requests", {"status": "success"})
        mc.increment("requests", {"status": "success"})
        assert mc.get_counter("requests", {"status": "success"}) == 2

    def test_record_timing(self):
        mc = MetricsCollector()
        mc.record("llm.latency", 150, {"model": "deepseek"})
        assert mc.get_latest("llm.latency", {"model": "deepseek"}) == 150

    def test_summary(self):
        mc = MetricsCollector()
        mc.increment("agent.request.total", {"status": "success"})
        mc.record("agent.stage.duration", 1200, {"stage": "llm"})
        summary = mc.summary()
        assert "agent.request.total" in summary
        assert "agent.stage.duration" in summary
