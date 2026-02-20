from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, Text

from app.database import Base


class Trace(Base):
    __tablename__ = "traces"

    trace_id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float)
    span_count = Column(Integer, default=0)
    status = Column(Text, default="unset")
    tags = Column(Text, default="{}")
    total_cost_usd = Column(Float, default=0)
    total_tokens = Column(Integer, default=0)
    created_at = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_traces_created_at", "created_at"),
        Index("idx_traces_status", "status"),
    )


class Span(Base):
    __tablename__ = "spans"

    span_id = Column(Text, primary_key=True)
    trace_id = Column(
        Text,
        ForeignKey("traces.trace_id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_span_id = Column(Text)
    span_type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    status = Column(Text, default="unset")
    error_message = Column(Text)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float)
    attributes = Column(Text, default="{}")
    annotations = Column(Text, default="[]")
    created_at = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_spans_trace_id", "trace_id"),
        Index("idx_spans_parent_span_id", "parent_span_id"),
        Index("idx_spans_span_type", "span_type"),
        Index("idx_spans_start_time", "start_time"),
        Index("idx_spans_name", "name"),
    )


class ReplayRun(Base):
    __tablename__ = "replay_runs"

    replay_id = Column(Text, primary_key=True)
    original_span_id = Column(
        Text, ForeignKey("spans.span_id", ondelete="CASCADE"), nullable=False
    )
    trace_id = Column(
        Text, ForeignKey("traces.trace_id", ondelete="CASCADE"), nullable=False
    )
    modified_input = Column(Text, nullable=False)
    new_output = Column(Text, nullable=False)
    diff = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False)
