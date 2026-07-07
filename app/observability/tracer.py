import uuid
from datetime import datetime, timezone
from pydantic import BaseModel


class TraceSpan(BaseModel):
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    node_id: str
    node_type: str
    status: str
    duration_ms: int
    input: str | None = None
    output: str | None = None
    error: str | None = None
    timestamp: datetime | None = None
    token_usage: dict | None = None


class Trace(BaseModel):
    trace_id: str
    node_type: str
    node_id: str
    spans: list[TraceSpan] = []


class Tracer:
    """Lightweight trace context manager for Agent/Workflow execution."""

    def __init__(self):
        self._traces: dict[str, Trace] = {}

    def create_trace(self, node_type: str, node_id: str) -> Trace:
        trace = Trace(trace_id=str(uuid.uuid4()), node_type=node_type, node_id=node_id)
        self._traces[trace.trace_id] = trace
        return trace

    def add_span(
        self, trace_id: str, node_id: str, node_type: str,
        status: str, duration_ms: int, parent_span_id: str | None = None,
        input: str | None = None, output: str | None = None, error: str | None = None,
    ) -> TraceSpan:
        trace = self._traces.get(trace_id)
        if trace is None:
            raise ValueError(f"Trace '{trace_id}' not found")
        span = TraceSpan(
            span_id=str(uuid.uuid4()), trace_id=trace_id,
            parent_span_id=parent_span_id, node_id=node_id,
            node_type=node_type, status=status, duration_ms=duration_ms,
            input=input, output=output, error=error,
            timestamp=datetime.now(timezone.utc),
        )
        trace.spans.append(span)
        return span

    def get_trace(self, trace_id: str) -> Trace | None:
        return self._traces.get(trace_id)
